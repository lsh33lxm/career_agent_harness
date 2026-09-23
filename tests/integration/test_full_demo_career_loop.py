from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from career_harness.api.offline_career_loop import (
    OfflineCareerLoopApi,
    create_offline_career_loop_router,
)
from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.resume import ResumePatchStatus, RevisionRef
from career_harness.db.knowledge_repository import KnowledgeRepository
from career_harness.db.memory_repository import MemoryRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.resume_studio_repository import ResumeStudioRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform import AppPaths
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
    assert result.application_state == "preparing"
    assert result.application_revision == 1
    assert result.interview_id is None
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
    assert story["steps"][-1]["status"] == "尚未建立关联"
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

    assert result.application_state == "preparing"
    assert studio.repository.resumes.get_base("resume_demo") is not None
    assert studio.repository.resumes.get_revision("resume_demo_revision") is not None
    assert loop.demo_story()["available"] is True


def test_demo_story_api_is_disabled_outside_demo_mode() -> None:
    app = FastAPI()
    app.include_router(create_offline_career_loop_router(OfflineCareerLoopApi(None)))
    response = TestClient(app).get("/api/v1/career-loop/demo-story")
    assert response.status_code == 403
    assert response.json()["detail"] == "该演示流程仅在隔离 Demo Mode 中可用"


def test_demo_runtime_requires_explicit_isolated_data_directory(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ACH_DATA_DIR", raising=False)
    with pytest.raises(ValueError, match="explicit isolated ACH_DATA_DIR"):
        create_runtime_app(Settings(environment="demo"))
    paths = AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "isolated")})
    app = create_runtime_app(Settings(environment="demo"), paths)
    assert app.state.settings.environment == "demo"


def test_demo_user_review_creates_target_revision_before_submission(tmp_path: Path) -> None:
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

    started = loop.start_demo(
        resume_id="resume_demo",
        resume_revision_id="resume_demo_revision",
        candidate_id="candidate_demo",
    )
    application = loop.applications.repository.get(started.application_id)
    assert application is not None
    assert application.state.value == "preparing"
    assert application.resume_revision_id is None
    story = loop.demo_story()
    patches = story["resume_patches"]
    assert len(patches) == 3
    assert all(item["operations"][0]["requirement_ids"] for item in patches)
    by_path = {item["operations"][0]["target_path"]: item for item in patches}
    summary = by_path["/summary"]
    skill_keep = by_path["/skills/0"]
    skill_reject = by_path["/skills/1"]
    with pytest.raises(ValueError, match="仍有待人工审核"):
        loop.create_demo_resume_revision(application_id=started.application_id)
    with pytest.raises(ValueError, match="未找到待审核"):
        loop.approve_demo_resume(patch_id="patch_invalid", application_id=started.application_id)
    loop.approve_demo_resume(
        patch_id=summary["patch_id"],
        application_id=started.application_id,
        decision=ResumePatchStatus.ACCEPTED,
        edited_value="用户手动确认的演示摘要",
    )
    loop.approve_demo_resume(
        patch_id=skill_reject["patch_id"],
        application_id=started.application_id,
        decision=ResumePatchStatus.REJECTED,
    )
    loop.approve_demo_resume(
        patch_id=skill_keep["patch_id"],
        application_id=started.application_id,
        decision=ResumePatchStatus.ACCEPTED,
    )
    assert loop.demo_story()["resume_patches"][0]["operations"][0]["evidence_ids"]
    created = loop.create_demo_resume_revision(application_id=started.application_id)
    assert created["application_state"] == "preparing"
    application = loop.applications.repository.get(started.application_id)
    assert application is not None
    assert application.state.value == "preparing"
    assert application.resume_revision_id is not None
    assert application.resume_revision_id.startswith("resume_revision_demo_target_")
    target = studio.repository.resumes.get_revision(application.resume_revision_id)
    assert target is not None
    assert {ref.entity_id for ref in target.accepted_patch_refs} == {
        summary["patch_id"],
        skill_keep["patch_id"],
    }
    assert skill_reject["patch_id"] not in {ref.entity_id for ref in target.accepted_patch_refs}
    assert target.content["summary"] == "用户手动确认的演示摘要"
    assert (
        studio.repository.resumes.get_base("resume_demo", 1).sections["summary"]
        == "已确认的演示经历摘要"
    )
    assert application.submission_authority is None and application.submitted_at is None
    engine.dispose()
    database_url = sqlite_url(tmp_path / "fact-service.db")
    upgrade_to_head(database_url)
    reopened_engine = create_sqlite_engine(database_url)
    reopened_studio = ResumeStudioService(
        CommandService(reopened_engine),
        ResumeStudioRepository(reopened_engine, ArtifactStore(tmp_path / "artifacts")),
    )
    reopened_loop = OfflineCareerLoopService(
        OpportunityRadarService(reopened_engine, ArtifactStore(tmp_path / "artifacts")),
        reopened_studio,
        KnowledgeRepository(reopened_engine, ArtifactStore(tmp_path / "artifacts")),
        MemoryRepository(reopened_engine),
    )
    reread = reopened_loop.demo_story()
    assert reread["resume_revision_id"] == created["resume_revision_id"]
    assert {item["patch_id"]: item["review_status"] for item in reread["resume_patches"]} == {
        summary["patch_id"]: "accepted",
        skill_keep["patch_id"]: "accepted",
        skill_reject["patch_id"]: "rejected",
    }
    assert (
        reopened_loop.applications.repository.get(started.application_id).resume_revision_id
        == created["resume_revision_id"]
    )
    assert (
        reopened_loop.create_demo_resume_revision(application_id=started.application_id)[
            "resume_revision_id"
        ]
        == created["resume_revision_id"]
    )
