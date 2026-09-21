from __future__ import annotations

from pathlib import Path

import pytest

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.db.resume_studio_repository import ResumeStudioRepository
from career_harness.services.command_service import CommandService
from career_harness.services.resume_service import ResumeService
from career_harness.services.resume_studio_service import ResumeStudioService
from career_harness.storage import ArtifactStore
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
