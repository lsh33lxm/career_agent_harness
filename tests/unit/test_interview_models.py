from datetime import UTC, datetime

import pytest

from career_harness.core.interview import Interview, InterviewRound, InterviewStatus


def _interview(**overrides):  # type: ignore[no-untyped-def]
    fields = {
        "entity_id": "interview_001",
        "revision": 1,
        "application_id": "application_001",
        "application_revision": 3,
        "round": InterviewRound.TECHNICAL,
        "scheduled_at": datetime(2026, 1, 10, 9, 0, tzinfo=UTC),
        "created_by": "user",
    }
    return Interview(**(fields | overrides))


def test_interview_defaults_to_scheduled() -> None:
    interview = _interview()
    assert interview.status is InterviewStatus.SCHEDULED
    assert interview.evidence_refs == ()
    assert interview.schema_version == 1


def test_interview_evidence_refs_must_be_unique() -> None:
    with pytest.raises(ValueError, match="evidence refs must be unique"):
        _interview(evidence_refs=("evidence_001", "evidence_001"))


def test_interview_first_revision_must_be_scheduled() -> None:
    with pytest.raises(ValueError, match="first Interview revision must be scheduled"):
        _interview(status=InterviewStatus.COMPLETED)
    later = _interview(revision=2, status=InterviewStatus.CANCELLED)
    assert later.status is InterviewStatus.CANCELLED
