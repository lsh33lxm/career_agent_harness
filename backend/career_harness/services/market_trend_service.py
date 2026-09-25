"""Read-only assembly of the Broad Market Trend read model (contract 0.12.0, D-022).

The service only reads: it never writes any table, never recomputes or writes
InvestmentState and never mutates priorities, personal capability state or the
official ontology. Broad-scope market bindings are read with a read-only SELECT
because the capability repository exposes no cross-capability broad-binding
list read (follow-up: promote this scan into a repository list method).
Aggregation rules live in the pure builder; the service only assembles typed
inputs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.capability import MarketBinding, MarketBindingScope
from career_harness.core.market import BroadMarketTrend, build_broad_market_trend
from career_harness.db.models import CapabilityMarketBindingRow


class MarketTrendService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def build_trend(self, *, computed_at: datetime | None = None) -> BroadMarketTrend:
        return build_broad_market_trend(self._broad_market_bindings(), computed_at=computed_at)

    def _broad_market_bindings(self) -> tuple[MarketBinding, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(CapabilityMarketBindingRow)
                .where(CapabilityMarketBindingRow.market_scope == MarketBindingScope.BROAD.value)
                .order_by(CapabilityMarketBindingRow.binding_id)
            ).all()
        return tuple(
            MarketBinding(
                binding_id=row.binding_id,
                capability_id=row.capability_id,
                market_scope=MarketBindingScope(row.market_scope),
                source_evidence_refs=tuple(row.source_evidence_refs),
                opportunity_id=row.opportunity_id,
                job_requirement_id=row.job_requirement_id,
                observed_at=row.observed_at,
            )
            for row in rows
        )
