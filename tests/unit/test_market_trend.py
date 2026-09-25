from datetime import UTC, datetime

import pytest

from career_harness.core.capability import MarketBinding, MarketBindingScope
from career_harness.core.market import (
    BROAD_MARKET_TREND_VERSION,
    BroadMarketTrend,
    CapabilityTrend,
    build_broad_market_trend,
)

COMPUTED_AT = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _broad_binding(binding_id: str, capability_id: str, refs: tuple[str, ...]) -> MarketBinding:
    return MarketBinding(
        binding_id=binding_id,
        capability_id=capability_id,
        market_scope=MarketBindingScope.BROAD,
        source_evidence_refs=refs,
        observed_at=COMPUTED_AT,
    )


def _target_binding(binding_id: str, capability_id: str) -> MarketBinding:
    return MarketBinding(
        binding_id=binding_id,
        capability_id=capability_id,
        market_scope=MarketBindingScope.TARGET,
        source_evidence_refs=("evidence_target",),
        job_requirement_id="requirement_001",
        observed_at=COMPUTED_AT,
    )


def test_aggregates_broad_bindings_per_capability() -> None:
    trend = build_broad_market_trend(
        [
            _broad_binding("binding_b", "capability_a", ("evidence_002",)),
            _broad_binding("binding_a", "capability_a", ("evidence_001", "evidence_002")),
            _broad_binding("binding_c", "capability_b", ("evidence_003",)),
        ],
        computed_at=COMPUTED_AT,
    )

    assert trend.trend_version == BROAD_MARKET_TREND_VERSION
    assert trend.computed_at == COMPUTED_AT
    assert [item.capability_id for item in trend.items] == ["capability_a", "capability_b"]
    capability_a, capability_b = trend.items
    assert capability_a.binding_count == 2
    assert capability_a.binding_ids == ("binding_a", "binding_b")
    assert capability_a.source_evidence_refs == ("evidence_001", "evidence_002")
    assert capability_b.binding_count == 1
    assert capability_b.binding_ids == ("binding_c",)
    assert capability_b.source_evidence_refs == ("evidence_003",)


def test_records_input_binding_revision_set() -> None:
    trend = build_broad_market_trend(
        [
            _broad_binding("binding_b", "capability_a", ("evidence_002",)),
            _broad_binding("binding_a", "capability_a", ("evidence_001",)),
            _broad_binding("binding_c", "capability_b", ("evidence_003",)),
        ],
        computed_at=COMPUTED_AT,
    )

    # Market bindings are immutable single-revision records: the binding ID set
    # pins the exact input revision set used for the trend.
    assert trend.input_binding_ids == ("binding_a", "binding_b", "binding_c")


def test_deterministic_for_shuffled_input() -> None:
    bindings = [
        _broad_binding("binding_c", "capability_b", ("evidence_003",)),
        _broad_binding("binding_a", "capability_a", ("evidence_001", "evidence_002")),
        _broad_binding("binding_b", "capability_a", ("evidence_002",)),
    ]

    forward = build_broad_market_trend(bindings, computed_at=COMPUTED_AT)
    shuffled = build_broad_market_trend(list(reversed(bindings)), computed_at=COMPUTED_AT)

    assert shuffled == forward


def test_empty_input_yields_empty_trend() -> None:
    trend = build_broad_market_trend([], computed_at=COMPUTED_AT)

    assert trend.items == ()
    assert trend.input_binding_ids == ()


def test_target_scope_bindings_never_mix_into_broad_trend() -> None:
    trend = build_broad_market_trend(
        [
            _broad_binding("binding_broad", "capability_a", ("evidence_broad",)),
            _target_binding("binding_target", "capability_a"),
            _target_binding("binding_target_only", "capability_b"),
        ],
        computed_at=COMPUTED_AT,
    )

    assert [item.capability_id for item in trend.items] == ["capability_a"]
    assert trend.items[0].binding_ids == ("binding_broad",)
    assert trend.items[0].source_evidence_refs == ("evidence_broad",)
    assert trend.input_binding_ids == ("binding_broad",)


def test_capability_trend_rejects_noncanonical_aggregation() -> None:
    with pytest.raises(ValueError, match="binding count"):
        CapabilityTrend(
            capability_id="capability_a",
            binding_count=2,
            binding_ids=("binding_a",),
            source_evidence_refs=("evidence_001",),
        )
    with pytest.raises(ValueError, match="sorted and unique"):
        CapabilityTrend(
            capability_id="capability_a",
            binding_count=2,
            binding_ids=("binding_b", "binding_a"),
            source_evidence_refs=("evidence_001",),
        )


def test_broad_market_trend_rejects_noncanonical_items() -> None:
    item_a = CapabilityTrend(
        capability_id="capability_a",
        binding_count=1,
        binding_ids=("binding_a",),
        source_evidence_refs=("evidence_001",),
    )
    item_b = CapabilityTrend(
        capability_id="capability_b",
        binding_count=1,
        binding_ids=("binding_b",),
        source_evidence_refs=("evidence_002",),
    )
    with pytest.raises(ValueError, match="sorted by unique capability id"):
        BroadMarketTrend(
            items=(item_b, item_a),
            input_binding_ids=("binding_a", "binding_b"),
            computed_at=COMPUTED_AT,
        )
    with pytest.raises(ValueError, match="sorted union"):
        BroadMarketTrend(
            items=(item_a, item_b),
            input_binding_ids=("binding_a",),
            computed_at=COMPUTED_AT,
        )
