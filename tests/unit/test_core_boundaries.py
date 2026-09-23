from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_harness.core.commands import Command, RevisionConflict, require_expected_revision
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.evidence import ExtractedClaim, Fact
from career_harness.core.evidence.models import ClaimStatus, promote_claim_to_fact


def test_extracted_claim_is_not_a_fact() -> None:
    claim = ExtractedClaim(
        claim_id="claim_001",
        claim_type="candidate_skill",
        subject=EntityRef(entity_id="candidate_001", kind=EntityKind.CANDIDATE),
        proposed_value="Python",
        evidence_refs=("evidence_001",),
        extractor="fixture-parser",
        extractor_version="1",
        confidence=0.9,
    )

    assert claim.status is ClaimStatus.PROPOSED
    assert not isinstance(claim, Fact)
    with pytest.raises(TypeError, match="reviewed promotion command"):
        promote_claim_to_fact(claim)


def test_command_requires_revision_and_idempotency_key() -> None:
    with pytest.raises(ValidationError):
        Command(
            command_id="command_001",
            command_type="candidate.update",
            target=EntityRef(entity_id="candidate_001", kind=EntityKind.CANDIDATE),
            expected_revision=-1,
            idempotency_key="short",
            actor="user",
        )


def test_revision_conflict_is_explicit() -> None:
    with pytest.raises(RevisionConflict) as error:
        require_expected_revision(expected=2, actual=3)

    assert error.value.expected == 2
    assert error.value.actual == 3
