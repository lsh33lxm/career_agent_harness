from __future__ import annotations

import base64
from pathlib import Path

import pytest

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.db.resume_studio_repository import ResumeStudioRepository
from career_harness.services.command_service import CommandService
from career_harness.services.resume_service import ResumeService
from career_harness.services.resume_studio_service import ResumeStudioService
from career_harness.storage import ArtifactStore
from career_harness.workers.resume_typst import (
    TypstCompileResult,
    TypstCompilerIdentity,
    TypstWorker,
)
from tests.integration.test_fact_service import _engine


def _command(entity_id: str, kind: EntityKind, command_id: str, *, actor: str = "user") -> Command:
    return Command(
        command_id=command_id,
        command_type=f"{kind.value}.command",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=0,
        idempotency_key=f"idempotency-{command_id}",
        actor=actor,
    )


def _studio(tmp_path: Path) -> tuple[ResumeStudioService, ResumeStudioRepository]:
    engine = _engine(tmp_path)
    commands = CommandService(engine)
    resumes = ResumeService(commands)
    resumes.save_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_base"),
        candidate_id="candidate_001",
        sections={
            "name": "Minnn",
            "contact": "minnn@example.com",
            "summary": "Verified platform engineer",
            "skills": ["Python", "SQLite"],
        },
    )
    resumes.create_revision(
        _command("resume_revision_001", EntityKind.RESUME_REVISION, "command_revision"),
        resume_id="resume_001",
        base_revision=1,
        accepted_patch_refs=(),
    )
    repository = ResumeStudioRepository(
        engine,
        ArtifactStore(tmp_path / "artifacts"),
    )
    return ResumeStudioService(commands, repository), repository


def test_user_can_restore_immutable_revision_as_new_base(tmp_path: Path) -> None:
    studio, repository = _studio(tmp_path)
    restored = studio.resumes.restore_revision(
        _command("resume_001", EntityKind.RESUME, "command_restore").model_copy(
            update={"expected_revision": 1}
        ),
        revision_id="resume_revision_001",
    )
    assert restored.revision == 2
    assert restored.sections["name"] == "Minnn"
    assert repository.resumes.get_base("resume_001", 1) is not None


def test_user_can_restore_older_base_as_append_only_undo(tmp_path: Path) -> None:
    studio, repository = _studio(tmp_path)
    studio.resumes.save_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_edit").model_copy(
            update={"expected_revision": 1}
        ),
        candidate_id="candidate_001",
        sections={"name": "Minnn", "summary": "Temporary edit"},
    )

    restored = studio.resumes.restore_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_base_restore").model_copy(
            update={"expected_revision": 2}
        ),
        source_revision=1,
    )

    assert restored.revision == 3
    assert restored.sections["summary"] == "Verified platform engineer"
    assert repository.resumes.get_base("resume_001", 2).sections["summary"] == "Temporary edit"  # type: ignore[union-attr]


def test_target_profile_render_pdf_ats_and_exact_artifact_provenance(tmp_path: Path) -> None:
    service, repository = _studio(tmp_path)
    profile = service.create_target_profile(
        target_profile_id="target_profile_001",
        resume_id="resume_001",
        title="Platform Engineer",
        company="Example",
        opportunity_id=None,
        opportunity_revision=None,
        requirement_refs=(),
        keyword_gaps=("Kubernetes",),
        actor="user",
    )
    assert profile.status.value == "approved"
    run, report = service.render(
        resume_revision_id="resume_revision_001",
        target_profile_id=profile.target_profile_id,
        template_id=None,
        actor="user",
    )
    assert run.output_media_type == "application/pdf"
    assert run.template_version == "1.0.0"
    assert run.renderer.value == "html_css"
    assert run.renderer_plugin_id == "resume-render-html-builtin"
    assert len(run.input_sha256) == 64
    assert run.checks["text_layer"] is True
    assert report.status.value == "warnings"
    assert report.keyword_gaps == ("Kubernetes",)
    pdf = repository.read_render_artifact(run.render_run_id)
    assert pdf.count(b"/Type /Page ") == 1
    assert b"Verified platform engineer" in pdf
    assert repository.get_ats_report(run.render_run_id) == report
    assert repository.get_render(run.render_run_id) == run

    replay, replay_report = service.render(
        resume_revision_id="resume_revision_001",
        target_profile_id=profile.target_profile_id,
        template_id=None,
        actor="user",
    )
    assert replay == run
    assert replay_report == report

    review = service.review_render(
        render_run_id=run.render_run_id,
        decision="approved",
        reason="Layout and claims reviewed against the source revision.",
        actor="user",
    )
    assert repository.get_render_review(run.render_run_id) == review
    assert service.review_render(
        render_run_id=run.render_run_id,
        decision="approved",
        reason="Layout and claims reviewed against the source revision.",
        actor="user",
    ) == review
    with pytest.raises(ValueError, match="different review"):
        service.review_render(
            render_run_id=run.render_run_id,
            decision="rejected",
            reason="A later conflicting decision must not overwrite the first review.",
            actor="user",
        )


def test_target_profile_and_render_preserve_user_authority_and_diff(tmp_path: Path) -> None:
    service, repository = _studio(tmp_path)
    with pytest.raises(ValueError, match="only the user"):
        service.create_target_profile(
            target_profile_id="target_profile_bad",
            resume_id="resume_001",
            title="Role",
            company=None,
            opportunity_id=None,
            opportunity_revision=None,
            requirement_refs=(),
            keyword_gaps=(),
            actor="agent:resume",
        )
    profile = service.create_target_profile(
        target_profile_id="target_profile_002",
        resume_id="resume_001",
        title="Role",
        company=None,
        opportunity_id=None,
        opportunity_revision=None,
        requirement_refs=(),
        keyword_gaps=(),
        actor="user",
    )
    diff = service.diff("resume_revision_001")
    assert diff.resume_id == "resume_001"
    assert diff.claim_provenance == ()
    assert repository.list_patch_refs(profile.target_profile_id) == ()


def test_typst_render_uses_sandbox_checks_and_compiler_provenance(tmp_path: Path) -> None:
    service, repository = _studio(tmp_path)

    class Sandbox:
        identity = TypstCompilerIdentity(version="0.13.1", executable_sha256="b" * 64)

        def compile(self, source, *, timeout_seconds, max_output_bytes):  # type: ignore[no-untyped-def]
            assert "Minnn" in source
            assert (timeout_seconds, max_output_bytes) == (10.0, 10_000_000)
            return TypstCompileResult(
                pdf_base64=base64.b64encode(b"%PDF-1.7\ncompressed-fixture").decode(),
                page_count=2,
                text_layer=True,
                reading_order=True,
                layout=True,
            )

    service = ResumeStudioService(
        service.commands,
        repository,
        typst_worker=TypstWorker(Sandbox()),
    )
    run, report = service.render(
        resume_revision_id="resume_revision_001",
        target_profile_id=None,
        template_id="resume-render-typst",
        actor="user",
    )
    assert run.renderer_plugin_version == "1.0.0+compiler.bbbbbbbbbbbb"
    assert run.page_count == 2
    assert report.checks["text_layer"] is True
    assert report.checks["layout"] is True
    assert repository.read_render_artifact(run.render_run_id).startswith(b"%PDF-1.7")
