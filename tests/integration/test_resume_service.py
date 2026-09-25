from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.resume import (
    ResumePatchAction,
    ResumePatchOperation,
    ResumePatchStatus,
    RevisionRef,
)
from career_harness.db.models import (
    IdempotencyRecordRow,
    ResumeBaseRevisionRow,
    ResumePatchRevisionRow,
    ResumeRevisionRow,
)
from career_harness.services.command_service import CommandService
from career_harness.services.resume_service import ResumeService, canonical_value_hash
from tests.integration.test_fact_service import EVIDENCE_REF_ID, _engine


def _command(
    entity_id: str,
    kind: EntityKind,
    command_id: str,
    *,
    actor: str,
    expected_revision: int = 0,
) -> Command:
    return Command(
        command_id=command_id,
        command_type=f"{kind.value}.command",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=expected_revision,
        idempotency_key=f"idempotency-{command_id}",
        actor=actor,
    )


def _operation(*, expected_hash: str | None = None, evidence: str = EVIDENCE_REF_ID):
    return ResumePatchOperation(
        action=ResumePatchAction.SET,
        target_path="/summary",
        expected_value_hash=expected_hash or canonical_value_hash("Old summary"),
        proposed_value="Agent systems engineer",
        evidence_refs=(evidence,),
        reason="Align the verified project evidence with the target role.",
    )


def test_resume_base_patch_review_and_revision_flow(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = ResumeService(CommandService(engine))
    base_command = _command("resume_001", EntityKind.RESUME, "command_base", actor="user")
    base = service.save_base_revision(
        base_command,
        candidate_id="candidate_001",
        sections={"summary": "Old summary", "skills": ["Python"]},
    )
    assert base.revision == 1

    patch_command = _command(
        "patch_001", EntityKind.RESUME_PATCH, "command_patch", actor="agent:resume"
    )
    proposed = service.propose_patch(
        patch_command,
        resume_id=base.resume_id,
        base_revision=base.revision,
        operations=(_operation(),),
    )
    assert proposed.status is ResumePatchStatus.PROPOSED

    reviewed = service.review_patch(
        _command(
            "patch_001",
            EntityKind.RESUME_PATCH,
            "command_review",
            actor="user",
            expected_revision=1,
        ),
        decision=ResumePatchStatus.ACCEPTED,
        review_reason="Verified against the attached evidence.",
    )
    assert reviewed.status is ResumePatchStatus.ACCEPTED

    revision = service.create_revision(
        _command(
            "resume_revision_001",
            EntityKind.RESUME_REVISION,
            "command_revision",
            actor="user",
        ),
        resume_id=base.resume_id,
        base_revision=1,
        accepted_patch_refs=(RevisionRef(entity_id="patch_001", revision=2),),
    )
    assert revision.content == {"summary": "Agent systems engineer", "skills": ["Python"]}
    assert revision.content_sha256 == canonical_value_hash(revision.content)
    assert service.repository.get_revision("resume_revision_001") == revision


def test_resume_commands_enforce_user_gates_and_provenance(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = ResumeService(CommandService(engine))
    with pytest.raises(ValueError, match="only the user"):
        service.save_base_revision(
            _command("resume_001", EntityKind.RESUME, "command_agent_base", actor="agent:x"),
            candidate_id="candidate_001",
            sections={"summary": "Old summary"},
        )
    service.save_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_base", actor="user"),
        candidate_id="candidate_001",
        sections={"summary": "Old summary"},
    )
    with pytest.raises(ValueError, match="dangling EvidenceRef"):
        service.propose_patch(
            _command("patch_bad", EntityKind.RESUME_PATCH, "command_bad", actor="agent:x"),
            resume_id="resume_001",
            base_revision=1,
            operations=(_operation(evidence="evidence_missing"),),
        )
    assert service.repository.get_patch("patch_bad") is None


def test_user_can_propose_and_review_own_patch(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = ResumeService(CommandService(engine))
    service.save_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_base", actor="user"),
        candidate_id="candidate_001",
        sections={"summary": "Old summary"},
    )
    proposed = service.propose_patch(
        _command("patch_001", EntityKind.RESUME_PATCH, "command_patch", actor="user"),
        resume_id="resume_001",
        base_revision=1,
        operations=(_operation(),),
    )
    assert proposed.proposed_by_kind.value == "user"

    reviewed = service.review_patch(
        _command(
            "patch_001",
            EntityKind.RESUME_PATCH,
            "command_review",
            actor="user",
            expected_revision=1,
        ),
        decision=ResumePatchStatus.ACCEPTED,
        review_reason="I authored and verified this change.",
    )
    assert reviewed.status is ResumePatchStatus.ACCEPTED


def test_rule_patch_preserves_rule_actor_kind(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = ResumeService(CommandService(engine))
    service.save_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_base", actor="user"),
        candidate_id="candidate_001",
        sections={"summary": "Old summary"},
    )
    proposed = service.propose_patch(
        _command("patch_001", EntityKind.RESUME_PATCH, "command_patch", actor="rule:resume"),
        resume_id="resume_001",
        base_revision=1,
        operations=(_operation(),),
    )
    assert proposed.proposed_by_kind.value == "rule"


def test_revision_fails_loud_on_hash_drift_and_nonaccepted_patch(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = ResumeService(CommandService(engine))
    service.save_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_base", actor="user"),
        candidate_id="candidate_001",
        sections={"summary": "Old summary"},
    )
    service.propose_patch(
        _command("patch_001", EntityKind.RESUME_PATCH, "command_patch", actor="agent:x"),
        resume_id="resume_001",
        base_revision=1,
        operations=(_operation(expected_hash="0" * 64),),
    )
    with pytest.raises(ValueError, match="exact accepted"):
        service.create_revision(
            _command(
                "resume_revision_001",
                EntityKind.RESUME_REVISION,
                "command_revision_1",
                actor="user",
            ),
            resume_id="resume_001",
            base_revision=1,
            accepted_patch_refs=(RevisionRef(entity_id="patch_001", revision=1),),
        )
    service.review_patch(
        _command(
            "patch_001",
            EntityKind.RESUME_PATCH,
            "command_review",
            actor="user",
            expected_revision=1,
        ),
        decision=ResumePatchStatus.ACCEPTED,
        review_reason="Evidence checked.",
    )
    with pytest.raises(ValueError, match="expected_value_hash"):
        service.create_revision(
            _command(
                "resume_revision_001",
                EntityKind.RESUME_REVISION,
                "command_revision_2",
                actor="user",
            ),
            resume_id="resume_001",
            base_revision=1,
            accepted_patch_refs=(RevisionRef(entity_id="patch_001", revision=2),),
        )
    assert service.repository.get_revision("resume_revision_001") is None


def test_base_write_is_idempotent(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = ResumeService(CommandService(engine))
    command = _command("resume_001", EntityKind.RESUME, "command_base", actor="user")
    first = service.save_base_revision(
        command,
        candidate_id="candidate_001",
        sections={"summary": "Old summary"},
    )
    replay = service.save_base_revision(
        command,
        candidate_id="candidate_001",
        sections={"summary": "Old summary"},
    )
    assert replay == first
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ResumeBaseRevisionRow)) == 1
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 1
        assert session.scalar(select(func.count()).select_from(ResumePatchRevisionRow)) == 0
        assert session.scalar(select(func.count()).select_from(ResumeRevisionRow)) == 0
