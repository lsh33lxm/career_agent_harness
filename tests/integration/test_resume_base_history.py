from pathlib import Path

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.db.resume_repository import ResumeRepository
from career_harness.services.command_service import CommandService
from career_harness.services.resume_service import ResumeService
from tests.integration.test_fact_service import _engine


def _command(entity_id: str, kind: EntityKind, command_id: str, expected: int = 0) -> Command:
    return Command(
        command_id=command_id,
        command_type="resume.history",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=expected,
        idempotency_key=f"history-{command_id}",
        actor="user",
    )


def test_base_history_keeps_every_user_restore_point(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = ResumeService(CommandService(engine))
    service.save_base_revision(
        _command("resume_history", EntityKind.RESUME, "base"),
        candidate_id="candidate_history",
        sections={"name": "Minnn", "summary": "第一版"},
    )
    service.save_base_revision(
        _command("resume_history", EntityKind.RESUME, "base2", expected=1),
        candidate_id="candidate_history",
        sections={"name": "Minnn", "summary": "第二版"},
    )
    history = ResumeRepository(engine).list_base_revisions("resume_history")
    assert [item.revision for item in history] == [2, 1]
    assert history[1].sections["summary"] == "第一版"
