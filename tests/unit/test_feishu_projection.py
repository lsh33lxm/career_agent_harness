from datetime import UTC, datetime

import pytest

from career_harness.adapters import feishu_projection
from career_harness.adapters.feishu_projection import prepare_today_projection
from career_harness.core.common import EntityKind
from career_harness.core.opportunity import PriorityLevel
from career_harness.core.today import (
    TodayItem,
    TodayItemKind,
    TodayQueue,
    TodayReason,
    TodayReasonCode,
    TodaySourceRef,
)


def queue() -> TodayQueue:
    ref = TodaySourceRef(entity_id="application_a", kind=EntityKind.APPLICATION, revision=3)
    old = ref.model_copy(update={"revision": 1})
    return TodayQueue(
        generated_at=datetime(2026, 9, 21, tzinfo=UTC),
        input_revisions=(ref, old),
        items=(
            TodayItem(
                item_id="today:interview_prep:application_a",
                kind=TodayItemKind.INTERVIEW_PREP,
                source_refs=(ref, old),
                reasons=(
                    TodayReason(code=TodayReasonCode.INTERVIEW_PREP_DUE, explanation="准备面试"),
                ),
                user_priority=PriorityLevel.LOW,
                suggested_priority=PriorityLevel.HIGH,
                interview_at=datetime(2026, 9, 22, tzinfo=UTC),
            ),
        ),
    )


def test_projection_preserves_priority_authority_and_exact_historical_refs():
    source = queue()
    before = source.model_dump_json()
    preview = prepare_today_projection(source)
    assert preview.to_json_bytes() == prepare_today_projection(source).to_json_bytes()
    assert source.model_dump_json() == before
    assert preview.mode == "dry_run"
    assert preview.rows[0].ordinal == 1
    assert preview.rows[0].item.user_priority == PriorityLevel.LOW
    assert preview.rows[0].item.suggested_priority == PriorityLevel.HIGH
    assert preview.rows[0].item.source_refs[1].revision == 1
    assert preview.rows[0].item == source.items[0]
    changed = source.model_copy(update={"policy_version": "another-policy"})
    assert prepare_today_projection(changed).source_sha256 != preview.source_sha256


def test_missing_provenance_fails_loud():
    with pytest.raises(ValueError, match="exact input revisions"):
        prepare_today_projection(queue().model_copy(update={"input_revisions": ()}))


def test_empty_queue_stays_empty():
    assert prepare_today_projection(TodayQueue(generated_at=datetime.now(UTC))).rows == ()


@pytest.mark.parametrize("limit", ["MAX_PREVIEW_ROWS", "MAX_PREVIEW_BYTES"])
def test_limits_fail_without_truncation(monkeypatch, limit):
    monkeypatch.setattr(feishu_projection, limit, 0)
    with pytest.raises(ValueError, match="limit"):
        prepare_today_projection(queue())


def test_bypassed_model_validation_cannot_duplicate_or_reorder_queue():
    source = queue()
    with pytest.raises(ValueError, match="unique item"):
        prepare_today_projection(source.model_copy(update={"items": source.items * 2}))
