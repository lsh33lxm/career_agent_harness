from pathlib import Path

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.db.resume_studio_repository import ResumeStudioRepository
from career_harness.services.command_service import CommandService
from career_harness.services.offline_career_loop_service import OfflineCareerLoopService
from career_harness.services.opportunity_radar_service import OpportunityRadarService
from career_harness.services.resume_service import ResumeService
from career_harness.services.resume_studio_service import ResumeStudioService
from career_harness.storage import ArtifactStore
from tests.integration.test_fact_service import _engine


def _command(entity_id: str, kind: EntityKind, command_id: str) -> Command:
    return Command(
        command_id=command_id,
        command_type=f"{kind.value}.command",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=0,
        idempotency_key=f"offline-loop-{command_id}",
        actor="user",
    )


def test_offline_career_loop_is_review_gated_and_replayable(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    commands = CommandService(engine)
    resumes = ResumeService(commands)
    resumes.save_base_revision(
        _command("resume_loop", EntityKind.RESUME, "base_loop"),
        candidate_id="candidate_loop",
        sections={
            "name": "Minnn",
            "contact": "minnn@example.com",
            "summary": "Verified platform engineer",
            "skills": ["Python", "SQLite"],
        },
    )
    resumes.create_revision(
        _command("resume_loop_revision", EntityKind.RESUME_REVISION, "revision_loop"),
        resume_id="resume_loop",
        base_revision=1,
        accepted_patch_refs=(),
    )
    artifacts = ArtifactStore(tmp_path / "artifacts")
    studio = ResumeStudioService(
        commands,
        ResumeStudioRepository(engine, artifacts),
    )
    loop = OfflineCareerLoopService(
        OpportunityRadarService(engine, artifacts),
        studio,
    )

    result = loop.run(
        resume_id="resume_loop",
        resume_revision_id="resume_loop_revision",
        candidate_id="candidate_loop",
    )

    assert result.opportunity_id.startswith("opportunity_")
    assert result.evidence_ref_id.startswith("evidence_job_staging_")
    assert result.patch_id is not None
    assert result.ats_status in {"passed", "warnings"}
    assert result.application_state == "preparing"
    assert result.application_revision == 1
    assert studio.repository.resumes.get_patch(result.patch_id) is not None
    assert studio.repository.get_render(result.render_run_id) is not None
    assert studio.repository.get_render_review(result.render_run_id) is None
