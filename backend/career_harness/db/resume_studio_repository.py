from __future__ import annotations

import difflib
import hashlib
import json
import time
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.evidence.models import ArtifactClass
from career_harness.core.job import JobRequirementStatus
from career_harness.core.resume import (
    AtsReportStatus,
    RenderRunStatus,
    ResumeAtsReport,
    ResumeRenderRun,
    ResumeStudioDiff,
    ResumeTargetPatchRef,
    ResumeTargetProfile,
    ResumeTemplateRegistration,
    RevisionRef,
    TargetProfileStatus,
    TemplateRenderer,
)
from career_harness.db.job_repository import JobRepository
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.resume_repository import ResumeRepository
from career_harness.storage import ArtifactStore


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    return json.loads(value) if isinstance(value, str) else value


class ResumeStudioRepository:
    def __init__(
        self,
        engine: Engine,
        artifact_store: ArtifactStore,
        *,
        resumes: ResumeRepository | None = None,
        jobs: JobRepository | None = None,
        opportunities: OpportunityRepository | None = None,
    ) -> None:
        self.engine = engine
        self.artifact_store = artifact_store
        self.resumes = resumes or ResumeRepository(engine)
        self.jobs = jobs or JobRepository(engine)
        self.opportunities = opportunities or OpportunityRepository(engine)

    def create_target_profile(self, profile: ResumeTargetProfile) -> ResumeTargetProfile:
        if self.resumes.get_base(profile.resume_id) is None:
            raise ValueError("ResumeTargetProfile requires an exact ResumeBase")
        opportunity = None
        if profile.opportunity_id is not None:
            if profile.opportunity_revision is None:
                raise ValueError("target opportunity requires an exact revision")
            opportunity = self.opportunities.get_revision(
                profile.opportunity_id, profile.opportunity_revision
            )
            if opportunity is None:
                raise ValueError("target opportunity revision does not exist")
        self._validate_requirements(profile.requirement_refs, opportunity)
        with self.engine.begin() as connection:
            existing = connection.execute(
                text(
                    "SELECT * FROM resume_target_profile "
                    "WHERE target_profile_id=:target_profile_id"
                ),
                {"target_profile_id": profile.target_profile_id},
            ).mappings().first()
            if existing is not None:
                current = self._target_profile(existing)
                if current != profile:
                    raise ValueError("target profile id already exists with different content")
                return current
            connection.execute(
                text(
                    "INSERT INTO resume_target_profile "
                    "(target_profile_id, resume_id, title, company, opportunity_id, "
                    "opportunity_revision, requirement_refs, keyword_gaps, status, "
                    "created_by, created_at) VALUES (:id, :resume_id, :title, :company, "
                    ":opportunity_id, :opportunity_revision, :requirement_refs, "
                    ":keyword_gaps, :status, :created_by, :created_at)"
                ),
                {
                    "id": profile.target_profile_id,
                    "resume_id": profile.resume_id,
                    "title": profile.title,
                    "company": profile.company,
                    "opportunity_id": profile.opportunity_id,
                    "opportunity_revision": profile.opportunity_revision,
                    "requirement_refs": _json(
                        [item.model_dump(mode="json") for item in profile.requirement_refs]
                    ),
                    "keyword_gaps": _json(list(profile.keyword_gaps)),
                    "status": profile.status.value,
                    "created_by": profile.created_by,
                    "created_at": profile.created_at,
                },
            )
            self._event(
                connection,
                "resume.target_profile.created",
                profile.target_profile_id,
                {
                    "resume_id": profile.resume_id,
                    "requirement_count": len(profile.requirement_refs),
                },
                profile.created_at,
            )
        return profile

    def get_target_profile(self, target_profile_id: str) -> ResumeTargetProfile | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM resume_target_profile WHERE target_profile_id=:id"),
                {"id": target_profile_id},
            ).mappings().first()
        return self._target_profile(row) if row else None

    def list_target_profiles(self, resume_id: str | None = None) -> tuple[ResumeTargetProfile, ...]:
        query = "SELECT * FROM resume_target_profile"
        params: dict[str, Any] = {}
        if resume_id is not None:
            query += " WHERE resume_id=:resume_id"
            params["resume_id"] = resume_id
        query += " ORDER BY created_at DESC, target_profile_id"
        with self.engine.connect() as connection:
            rows = connection.execute(text(query), params).mappings().all()
        return tuple(self._target_profile(row) for row in rows)

    def link_patch(
        self, target_profile_id: str, patch_id: str, patch_revision: int
    ) -> ResumeTargetPatchRef:
        profile = self.get_target_profile(target_profile_id)
        if profile is None:
            raise KeyError("target profile not found")
        patch = self.resumes.get_patch(patch_id, patch_revision)
        if patch is None:
            raise ValueError("target patch reference requires an exact ResumePatch")
        if patch.resume_id != profile.resume_id:
            raise ValueError("target patch does not belong to the selected Resume")
        ref = ResumeTargetPatchRef(
            target_profile_id=target_profile_id,
            patch_id=patch_id,
            patch_revision=patch_revision,
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO resume_target_patch_ref "
                    "(target_profile_id, patch_id, patch_revision) VALUES "
                    "(:target_profile_id, :patch_id, :patch_revision)"
                ),
                ref.model_dump(),
            )
        return ref

    def list_patch_refs(self, target_profile_id: str) -> tuple[ResumeTargetPatchRef, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT target_profile_id, patch_id, patch_revision "
                    "FROM resume_target_patch_ref WHERE target_profile_id=:id "
                    "ORDER BY patch_id, patch_revision"
                ),
                {"id": target_profile_id},
            ).mappings().all()
        return tuple(ResumeTargetPatchRef(**dict(row)) for row in rows)

    def ensure_template(
        self, template: ResumeTemplateRegistration, definition: dict[str, Any]
    ) -> ResumeTemplateRegistration:
        with self.engine.begin() as connection:
            row = connection.execute(
                text("SELECT * FROM resume_template_registration WHERE template_id=:id"),
                {"id": template.template_id},
            ).mappings().first()
            if row is not None:
                current = self._template(row)
                if current.content_sha256 != template.content_sha256:
                    raise RuntimeError("registered resume template hash changed")
                return current
            connection.execute(
                text(
                    "INSERT INTO resume_template_registration "
                    "(template_id, name, version, renderer, content_sha256, description, "
                    "definition, status, created_at) VALUES (:id, :name, :version, "
                    ":renderer, :content_sha256, :description, :definition, :status, :created_at)"
                ),
                {
                    **template.model_dump(mode="json", exclude={"created_at"}),
                    "id": template.template_id,
                    "renderer": template.renderer.value,
                    "definition": _json(definition),
                    "created_at": template.created_at,
                },
            )
            self._event(
                connection,
                "resume.template.registered",
                template.template_id,
                {"version": template.version, "content_sha256": template.content_sha256},
                template.created_at,
            )
        return template

    def get_template(self, template_id: str) -> ResumeTemplateRegistration | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM resume_template_registration WHERE template_id=:id"),
                {"id": template_id},
            ).mappings().first()
        return self._template(row) if row else None

    def list_templates(self) -> tuple[ResumeTemplateRegistration, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("SELECT * FROM resume_template_registration ORDER BY template_id")
            ).mappings().all()
        return tuple(self._template(row) for row in rows)

    def persist_render(
        self,
        run: ResumeRenderRun,
        report: ResumeAtsReport,
        pdf_bytes: bytes,
    ) -> ResumeRenderRun:
        artifact = self.artifact_store.put(pdf_bytes, ArtifactClass.PERSONAL)
        artifact_id = run.output_artifact_id
        if artifact.sha256 != run.output_sha256:
            raise ValueError("render output hash does not match Artifact Store")
        now = run.created_at
        with self.engine.begin() as connection:
            existing = connection.execute(
                text("SELECT * FROM resume_render_run WHERE render_run_id=:id"),
                {"id": run.render_run_id},
            ).mappings().first()
            if existing is not None:
                current = self._render(existing)
                if current.output_sha256 != run.output_sha256:
                    raise ValueError("render run id already exists with different output")
                return current
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO evidence_artifact "
                    "(artifact_id, sha256, media_type, artifact_class, byte_length) "
                    "VALUES (:id, :sha256, 'application/pdf', 'personal', :byte_length)"
                ),
                {"id": artifact_id, "sha256": artifact.sha256, "byte_length": artifact.byte_length},
            )
            connection.execute(
                text(
                    "INSERT INTO resume_render_run "
                    "(render_run_id, resume_revision_id, target_profile_id, template_id, status, "
                    "output_artifact_id, output_sha256, output_media_type, page_count, "
                    "preview_html, checks, created_by, created_at) VALUES "
                    "(:render_run_id, :resume_revision_id, :target_profile_id, :template_id, "
                    ":status, :output_artifact_id, :output_sha256, :output_media_type, "
                    ":page_count, :preview_html, :checks, :created_by, :created_at)"
                ),
                {
                    "render_run_id": run.render_run_id,
                    "resume_revision_id": run.resume_revision_id,
                    "target_profile_id": run.target_profile_id,
                    "template_id": run.template_id,
                    "status": run.status.value,
                    "output_artifact_id": run.output_artifact_id,
                    "output_sha256": run.output_sha256,
                    "output_media_type": run.output_media_type,
                    "page_count": run.page_count,
                    "preview_html": run.preview_html,
                    "checks": _json(run.checks),
                    "created_by": run.created_by,
                    "created_at": now,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO resume_ats_report "
                    "(render_run_id, status, page_count, checks, keyword_gaps, created_at) "
                    "VALUES (:render_run_id, :status, :page_count, :checks, "
                    ":keyword_gaps, :created_at)"
                ),
                {
                    "render_run_id": report.render_run_id,
                    "status": report.status.value,
                    "page_count": report.page_count,
                    "checks": _json(report.checks),
                    "keyword_gaps": _json(list(report.keyword_gaps)),
                    "created_at": report.created_at,
                },
            )
            self._event(
                connection,
                "resume.render.completed",
                run.render_run_id,
                {
                    "resume_revision_id": run.resume_revision_id,
                    "target_profile_id": run.target_profile_id,
                    "template_id": run.template_id,
                    "output_artifact_id": artifact_id,
                    "output_sha256": run.output_sha256,
                    "ats_status": report.status.value,
                },
                now,
            )
        return run

    def get_render(self, render_run_id: str) -> ResumeRenderRun | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM resume_render_run WHERE render_run_id=:id"),
                {"id": render_run_id},
            ).mappings().first()
        return self._render(row) if row else None

    def get_ats_report(self, render_run_id: str) -> ResumeAtsReport | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM resume_ats_report WHERE render_run_id=:id"),
                {"id": render_run_id},
            ).mappings().first()
        if row is None:
            return None
        return ResumeAtsReport(
            render_run_id=row["render_run_id"],
            status=AtsReportStatus(row["status"]),
            page_count=row["page_count"],
            checks=dict(_loads(row["checks"], {})),
            keyword_gaps=tuple(_loads(row["keyword_gaps"], [])),
            created_at=row["created_at"],
        )

    def read_render_artifact(self, render_run_id: str) -> bytes:
        run = self.get_render(render_run_id)
        if run is None:
            raise KeyError("render run not found")
        return self.artifact_store.read(run.output_sha256)

    def diff(self, resume_revision_id: str) -> ResumeStudioDiff:
        revision = self.resumes.get_revision(resume_revision_id)
        if revision is None:
            raise KeyError("resume revision not found")
        base = self.resumes.get_base(revision.resume_id, revision.base_revision)
        if base is None:
            raise RuntimeError("resume revision base is missing")
        left = json.dumps(
            base.sections, ensure_ascii=False, indent=2, sort_keys=True
        ).splitlines()
        right = json.dumps(
            revision.content, ensure_ascii=False, indent=2, sort_keys=True
        ).splitlines()
        claim_refs: list[RevisionRef] = []
        evidence_refs: list[str] = []
        for patch_ref in revision.accepted_patch_refs:
            patch = self.resumes.get_patch(patch_ref.entity_id, patch_ref.revision)
            if patch is None:
                raise RuntimeError("resume revision has a dangling patch reference")
            for operation in patch.operations:
                claim_refs.extend(operation.fact_refs)
                evidence_refs.extend(operation.evidence_refs)
        return ResumeStudioDiff(
            resume_id=revision.resume_id,
            base_revision=revision.base_revision,
            resume_revision_id=revision.revision_id,
            diff="\n".join(
                difflib.unified_diff(
                    left,
                    right,
                    fromfile=f"{revision.resume_id}#base-{revision.base_revision}",
                    tofile=revision.revision_id,
                    lineterm="",
                )
            ),
            claim_provenance=tuple(dict.fromkeys(claim_refs)),
            evidence_provenance=tuple(dict.fromkeys(evidence_refs)),
        )

    def _validate_requirements(self, refs: tuple[RevisionRef, ...], opportunity: Any) -> None:
        for ref in refs:
            requirement = self.jobs.get_requirement(ref.entity_id, ref.revision)
            if requirement is None or requirement.status is not JobRequirementStatus.ACCEPTED:
                raise ValueError("target profile requires exact accepted JobRequirement refs")
            if opportunity is not None and requirement.job != opportunity.job:
                raise ValueError("target requirement does not belong to the selected Opportunity")

    @staticmethod
    def _event(
        connection: Any,
        event_type: str,
        entity_id: str,
        payload: dict[str, Any],
        occurred_at: datetime,
    ) -> None:
        connection.execute(
            text(
                "INSERT INTO domain_event "
                "(event_id, event_type, entity_id, entity_revision, command_id, payload, "
                "occurred_at) VALUES (:event_id, :event_type, :entity_id, 1, :command_id, "
                ":payload, :occurred_at)"
            ),
            {
                "event_id": (
                    "event_resume_studio_"
                    + hashlib.sha256((event_type + entity_id).encode()).hexdigest()[:32]
                    + f"_{time.time_ns()}"
                ),
                "event_type": event_type,
                "entity_id": entity_id,
                "command_id": f"resume_studio_{event_type.replace('.', '_')}_{entity_id}",
                "payload": _json(payload),
                "occurred_at": occurred_at,
            },
        )

    @staticmethod
    def _target_profile(row: Any) -> ResumeTargetProfile:
        return ResumeTargetProfile(
            target_profile_id=row["target_profile_id"],
            resume_id=row["resume_id"],
            title=row["title"],
            company=row["company"],
            opportunity_id=row["opportunity_id"],
            opportunity_revision=row["opportunity_revision"],
            requirement_refs=tuple(
                RevisionRef.model_validate(item) for item in _loads(row["requirement_refs"], [])
            ),
            keyword_gaps=tuple(_loads(row["keyword_gaps"], [])),
            status=TargetProfileStatus(row["status"]),
            created_by=row["created_by"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _template(row: Any) -> ResumeTemplateRegistration:
        return ResumeTemplateRegistration(
            template_id=row["template_id"],
            name=row["name"],
            version=row["version"],
            renderer=TemplateRenderer(row["renderer"]),
            content_sha256=row["content_sha256"],
            description=row["description"],
            status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _render(row: Any) -> ResumeRenderRun:
        return ResumeRenderRun(
            render_run_id=row["render_run_id"],
            resume_revision_id=row["resume_revision_id"],
            target_profile_id=row["target_profile_id"],
            template_id=row["template_id"],
            status=RenderRunStatus(row["status"]),
            output_artifact_id=row["output_artifact_id"],
            output_sha256=row["output_sha256"],
            output_media_type=row["output_media_type"],
            page_count=row["page_count"],
            preview_html=row["preview_html"],
            checks=dict(_loads(row["checks"], {})),
            created_by=row["created_by"],
            created_at=row["created_at"],
        )
