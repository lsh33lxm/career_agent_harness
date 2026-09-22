from pathlib import Path

import pytest

from career_harness.core.communication import (
    CommunicationChannel,
    CommunicationDraft,
    CommunicationStatus,
)
from career_harness.db.communication_repository import CommunicationRepository
from tests.integration.test_fact_service import _engine


def test_communication_draft_is_proposal_only_and_user_reviewed(tmp_path: Path) -> None:
    repository = CommunicationRepository(_engine(tmp_path))
    draft = repository.create(
        CommunicationDraft(
            draft_id="draft_fixture_001",
            opportunity_id="opportunity_fixture_001",
            source_staging_id="staging_fixture_001",
            channel=CommunicationChannel.FOLLOW_UP_NOTE,
            recipient="recruiter@example.com",
            body="您好，想确认该岗位目前的面试安排。",
            provenance={"source": "offline_fixture", "created_for": "review"},
            created_by="user",
        )
    )
    assert draft.status is CommunicationStatus.PENDING_REVIEW
    approved = repository.review(
        draft.draft_id,
        decision=CommunicationStatus.APPROVED,
        reason="用户确认措辞，但仍需在外部平台手动发送。",
    )
    assert approved.status is CommunicationStatus.APPROVED
    assert approved.reviewed_by == "user"
    assert repository.review(
        draft.draft_id,
        decision=CommunicationStatus.APPROVED,
        reason="用户确认措辞，但仍需在外部平台手动发送。",
    ) == approved
    with pytest.raises(ValueError, match="不能覆盖"):
        repository.review(draft.draft_id, decision=CommunicationStatus.REJECTED, reason="改写")


def test_communication_summary_tracks_daily_limit_and_statuses(tmp_path: Path) -> None:
    repository = CommunicationRepository(_engine(tmp_path))
    statuses = (
        CommunicationStatus.PENDING_REVIEW,
        CommunicationStatus.REPLIED,
        CommunicationStatus.FOLLOW_UP,
    )
    for index, status in enumerate(statuses):
        repository.create(
            CommunicationDraft(
                draft_id=f"draft_summary_{index}",
                opportunity_id="opportunity_summary_001",
                channel=CommunicationChannel.FOLLOW_UP_NOTE,
                body=f"草稿 {index}",
                status=status,
                created_by="user",
            )
        )
    summary = repository.summary(daily_limit=5)
    assert summary["created_today"] == 3
    assert summary["remaining_today"] == 2
    assert summary["reply_count"] == 1
    assert summary["follow_up_count"] == 1
    assert summary["counts"][CommunicationStatus.PENDING_REVIEW.value] == 1


def test_communication_state_transitions_are_explicit_and_local(tmp_path: Path) -> None:
    repository = CommunicationRepository(_engine(tmp_path))
    draft = repository.create(
        CommunicationDraft(
            draft_id="draft_transition_001",
            opportunity_id="opportunity_transition_001",
            channel=CommunicationChannel.FOLLOW_UP_NOTE,
            body="人工确认后的草稿",
            status=CommunicationStatus.APPROVED,
            created_by="user",
        )
    )
    sent = repository.transition(draft.draft_id, status=CommunicationStatus.SENT)
    assert sent.status is CommunicationStatus.SENT
    replied = repository.transition(draft.draft_id, status=CommunicationStatus.REPLIED)
    assert replied.status is CommunicationStatus.REPLIED
    follow_up = repository.transition(draft.draft_id, status=CommunicationStatus.FOLLOW_UP)
    assert follow_up.status is CommunicationStatus.FOLLOW_UP
    with pytest.raises(ValueError, match="不允许"):
        repository.transition(draft.draft_id, status=CommunicationStatus.PENDING_REVIEW)
