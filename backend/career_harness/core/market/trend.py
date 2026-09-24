"""Core-owned Broad Market Trend read model (contract 0.12.0, D-022).

A Broad Market Trend is a derived read model aggregating broad-scope
``MarketBinding`` records per capability: counts, exact source refs and the
binding set used. It is computed on read and never persisted as truth. Market
bindings are immutable single-revision records, so a binding ID pins the exact
input revision; the trend's input set is therefore the sorted set of binding
IDs used.

Trends inform exploration, discovery and validation only: they never drive
investment decisions, never reweight target-scope inputs and never mutate
priorities or personal capability state. Equal inputs always produce equal
output regardless of input order; empty inputs yield an empty trend.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from pydantic import Field, field_validator, model_validator

from career_harness.core.capability import MarketBinding, MarketBindingScope
from career_harness.core.common import FrozenModel, OpaqueId, utc_now

BROAD_MARKET_TREND_VERSION = "broad-market-trend-v1"


def _aware(value: datetime) -> datetime:
    # SQLite returns naive datetimes; normalize to UTC like the Today model.
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class CapabilityTrend(FrozenModel):
    """Aggregated broad-scope market signal for one capability."""

    capability_id: OpaqueId
    binding_count: int = Field(ge=1)
    binding_ids: tuple[OpaqueId, ...] = Field(min_length=1)
    source_evidence_refs: tuple[OpaqueId, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def aggregation_is_canonical(self) -> CapabilityTrend:
        if self.binding_count != len(self.binding_ids):
            raise ValueError("binding count must equal the number of bindings aggregated")
        if self.binding_ids != tuple(sorted(set(self.binding_ids))):
            raise ValueError("trend binding ids must be sorted and unique")
        if self.source_evidence_refs != tuple(sorted(set(self.source_evidence_refs))):
            raise ValueError("trend source evidence refs must be sorted and unique")
        return self


class BroadMarketTrend(FrozenModel):
    """Derived per-capability broad market trend with its input revision set."""

    items: tuple[CapabilityTrend, ...] = ()
    input_binding_ids: tuple[OpaqueId, ...] = ()
    computed_at: datetime = Field(default_factory=utc_now)
    trend_version: str = BROAD_MARKET_TREND_VERSION

    @field_validator("computed_at")
    @classmethod
    def computed_at_is_utc_aware(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def trend_is_canonical(self) -> BroadMarketTrend:
        capability_ids = [item.capability_id for item in self.items]
        if capability_ids != sorted(set(capability_ids)):
            raise ValueError("trend items must be sorted by unique capability id")
        expected_inputs = tuple(
            sorted({binding_id for item in self.items for binding_id in item.binding_ids})
        )
        if self.input_binding_ids != expected_inputs:
            raise ValueError("trend input binding ids must be the sorted union of item inputs")
        return self


def build_broad_market_trend(
    bindings: Iterable[MarketBinding], *, computed_at: datetime | None = None
) -> BroadMarketTrend:
    """Aggregate broad-scope market bindings per capability, deterministically.

    Target-scope bindings are never mixed into the broad aggregation. Output is
    independent of input ordering; empty input yields an empty trend.
    """

    grouped: dict[str, list[MarketBinding]] = {}
    for binding in bindings:
        if binding.market_scope is not MarketBindingScope.BROAD:
            continue
        grouped.setdefault(binding.capability_id, []).append(binding)
    items = tuple(
        CapabilityTrend(
            capability_id=capability_id,
            binding_count=len(capability_bindings),
            binding_ids=tuple(sorted(binding.binding_id for binding in capability_bindings)),
            source_evidence_refs=tuple(
                sorted(
                    {ref for binding in capability_bindings for ref in binding.source_evidence_refs}
                )
            ),
        )
        for capability_id, capability_bindings in sorted(grouped.items())
    )
    return BroadMarketTrend(
        items=items,
        input_binding_ids=tuple(
            sorted({binding_id for item in items for binding_id in item.binding_ids})
        ),
        computed_at=computed_at or utc_now(),
    )
