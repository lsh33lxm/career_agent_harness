from pathlib import Path

from sqlalchemy import text

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.resume import ResumePatchStatus, RevisionRef
from career_harness.db.knowledge_repository import KnowledgeRepository
from career_harness.db.memory_repository import MemoryRepository
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
        command_type=f"{kind.value}.demo",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=0,
        idempotency_key=f"full-demo-{command_id}",
        actor="user",
    )


def test_full_demo_career_loop_persists_and_replays(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    commands = CommandService(engine)
    resumes = ResumeService(commands)
    resumes.save_base_revision(
        _command("resume_demo", EntityKind.RESUME, "base_demo"),
        candidate_id="candidate_demo",
        sections={
            "name": "演示候选人",
            "contact": "demo@example.invalid",
            "summary": "已确认的演示经历摘要",
            "skills": ["Python", "SQLite"],
        },
    )
    resumes.create_revision(
        _command("resume_demo_revision", EntityKind.RESUME_REVISION, "revision_demo"),
        resume_id="resume_demo",
        base_revision=1,
        accepted_patch_refs=(),
    )
    artifacts = ArtifactStore(tmp_path / "artifacts")
    studio = ResumeStudioService(commands, ResumeStudioRepository(engine, artifacts))
    loop = OfflineCareerLoopService(
        OpportunityRadarService(engine, artifacts),
        studio,
        KnowledgeRepository(engine, artifacts),
        MemoryRepository(engine),
    )

    result = loop.run_full_demo(
        resume_id="resume_demo",
        resume_revision_id="resume_demo_revision",
        candidate_id="candidate_demo",
    )
    replay = loop.run_full_demo(
        resume_id="resume_demo",
        resume_revision_id="resume_demo_revision",
        candidate_id="candidate_demo",
    )

    assert result.opportunity_id.startswith("opportunity_")
    assert result.application_state == "interview"
    assert result.application_revision == 4
    assert result.interview_id is not None
    assert result.interview_revision == 2
    assert result.interview_prep_proposal_id is not None
    assert result.interview_feedback_proposal_id is not None
    assert replay == result
    story = loop.demo_story()
    assert story["available"] is True
    assert story["application_id"] == result.application_id
    assert story["staging_id"] == result.staging_id
    assert story["evidence_ref_id"] == result.evidence_ref_id
    assert story["score"] == result.score
    assert story["gaps"] == list(result.gaps)
    assert len(result.requirement_ids) == 3
    assert len(story["requirements"]) == 3
    assert all(item["status"] == "proposed" for item in story["requirements"])
    assert story["resume_patch"]["patch_id"] == result.patch_id
    assert story["resume_patch"]["status"] == "proposed"
    assert [step["label"] for step in story["steps"]][-1] == "完成面试复盘"
    assert any(link["kind"] == "岗位" for link in story["links"])
    assert any(link["kind"] == "知识" for link in story["links"])

    assert result.patch_id is not None
    pending_patch = studio.repository.resumes.get_patch(result.patch_id, 1)
    assert pending_patch is not None
    assert pending_patch.status is ResumePatchStatus.PROPOSED
    review_command = Command(
        command_id="demo_patch_review",
        command_type="resume_patch.review",
        target=EntityRef(entity_id=result.patch_id, kind=EntityKind.RESUME_PATCH),
        expected_revision=1,
        idempotency_key="demo-patch-review",
        actor="user",
    )
    reviewed_patch = studio.resumes.review_patch(
        review_command,
        decision=ResumePatchStatus.ACCEPTED,
        review_reason="用户核对演示证据后接受该修改",
    )
    target_revision = studio.resumes.create_revision(
        _command("resume_demo_target_revision", EntityKind.RESUME_REVISION, "demo_target_revision"),
        resume_id="resume_demo",
        base_revision=1,
        accepted_patch_refs=(
            RevisionRef(entity_id=result.patch_id, revision=reviewed_patch.revision),
        ),
    )
    assert target_revision.accepted_patch_refs == (
        RevisionRef(entity_id=result.patch_id, revision=reviewed_patch.revision),
    )
    assert studio.repository.resumes.get_revision("resume_demo_target_revision") is not None

    with engine.connect() as connection:
        event_types = [
            row[0]
            for row in connection.execute(
                text(
                    "SELECT event_type FROM domain_event "
                    "WHERE entity_id IN (:app, :interview) "
                    "ORDER BY occurred_at, event_id"
                ),
                {"app": result.application_id, "interview": result.interview_id},
            )
        ]
    assert event_types == [
        "application.created",
        "application.state_changed",
        "application.submission_recorded",
        "application.state_changed",
        "interview.scheduled",
        "interview.completed",
    ]


def test_full_demo_loop_seeds_resume_in_an_empty_database(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    artifacts = ArtifactStore(tmp_path / "artifacts")
    commands = CommandService(engine)
    studio = ResumeStudioService(commands, ResumeStudioRepository(engine, artifacts))
    loop = OfflineCareerLoopService(
        OpportunityRadarService(engine, artifacts),
        studio,
        KnowledgeRepository(engine, artifacts),
        MemoryRepository(engine),
    )

    result = loop.run_full_demo(
        resume_id="resume_demo",
        resume_revision_id="resume_demo_revision",
        candidate_id="candidate_demo",
    )

    assert result.application_state == "interview"
    assert studio.repository.resumes.get_base("resume_demo") is not None
    assert studio.repository.resumes.get_revision("resume_demo_revision") is not None
    assert loop.demo_story()["available"] is True
