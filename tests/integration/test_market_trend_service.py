from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    Base,
    CapabilityIdentityRow,
    CapabilityMarketBindingRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.market_trend_service import MarketTrendService

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _engine(tmp_path: Path) -> Engine:
    database_url = sqlite_url(tmp_path / "market-trend-service.db")
    upgrade_to_head(database_url)
    return create_sqlite_engine(database_url)


def _table_counts(engine: Engine) -> dict[str, int]:
    with Session(engine) as session:
        return {
            table.name: session.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }


def _seed_market_bindings(engine: Engine) -> None:
    with engine.begin() as connection:
        for capability_id in ("capability_a", "capability_b"):
            connection.execute(
                CapabilityIdentityRow.__table__.insert(), {"capability_id": capability_id}
            )
        connection.execute(
            CapabilityMarketBindingRow.__table__.insert(),
            [
                {
                    "binding_id": "market_broad_b",
                    "capability_id": "capability_a",
                    "market_scope": "broad",
                    "source_evidence_refs": ["evidence_broad_2"],
                    "opportunity_id": None,
                    "job_requirement_id": None,
                    "observed_at": NOW,
                },
                {
                    "binding_id": "market_broad_a",
                    "capability_id": "capability_a",
                    "market_scope": "broad",
                    "source_evidence_refs": ["evidence_broad_1", "evidence_broad_2"],
                    "opportunity_id": None,
                    "job_requirement_id": None,
                    "observed_at": NOW,
                },
                {
                    "binding_id": "market_broad_c",
                    "capability_id": "capability_b",
                    "market_scope": "broad",
                    "source_evidence_refs": ["evidence_broad_3"],
                    "opportunity_id": None,
                    "job_requirement_id": None,
                    "observed_at": NOW,
                },
                {
                    "binding_id": "market_target",
                    "capability_id": "capability_a",
                    "market_scope": "target",
                    "source_evidence_refs": ["evidence_target"],
                    "opportunity_id": None,
                    "job_requirement_id": "requirement_001",
                    "observed_at": NOW,
                },
            ],
        )


def test_build_trend_aggregates_broad_bindings_only(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_market_bindings(engine)

    trend = MarketTrendService(engine).build_trend(computed_at=NOW)

    assert [item.capability_id for item in trend.items] == ["capability_a", "capability_b"]
    capability_a, capability_b = trend.items
    assert capability_a.binding_count == 2
    assert capability_a.binding_ids == ("market_broad_a", "market_broad_b")
    assert capability_a.source_evidence_refs == ("evidence_broad_1", "evidence_broad_2")
    assert capability_b.binding_count == 1
    assert capability_b.binding_ids == ("market_broad_c",)
    assert trend.input_binding_ids == (
        "market_broad_a",
        "market_broad_b",
        "market_broad_c",
    )


def test_build_trend_is_deterministic_and_never_writes(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_market_bindings(engine)
    service = MarketTrendService(engine)

    before = _table_counts(engine)
    first = service.build_trend(computed_at=NOW)
    second = service.build_trend(computed_at=NOW)
    after = _table_counts(engine)

    assert second == first
    assert after == before


def test_build_trend_empty_database_yields_empty_trend(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    trend = MarketTrendService(engine).build_trend(computed_at=NOW)

    assert trend.items == ()
    assert trend.input_binding_ids == ()
