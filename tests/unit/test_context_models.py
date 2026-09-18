from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from career_harness.core.context import (
    ContextAsset,
    ContextAssetClass,
    ContextAssetRef,
    ContextManifest,
    MarketEvidenceScope,
)


def test_context_asset_classes_are_the_five_contract_assets() -> None:
    assert {asset_class.value for asset_class in ContextAssetClass} == {
        "personal_context",
        "career_state",
        "project_evidence",
        "market_evidence",
        "career_history_outcome",
    }


def test_market_evidence_requires_target_or_broad_scope() -> None:
    with pytest.raises(ValidationError, match="market evidence requires"):
        ContextAsset(
            ref=ContextAssetRef(
                asset_id="market_001",
                asset_class=ContextAssetClass.MARKET_EVIDENCE,
                revision=1,
            ),
            title="Observed requirements",
            payload={"requirement": "OpenTelemetry"},
        )

    market = ContextAsset(
        ref=ContextAssetRef(
            asset_id="market_001",
            asset_class=ContextAssetClass.MARKET_EVIDENCE,
            revision=1,
        ),
        title="Observed requirements",
        payload={"requirement": "OpenTelemetry"},
        market_scope=MarketEvidenceScope.TARGET,
    )

    assert market.market_scope is MarketEvidenceScope.TARGET


def test_non_market_asset_cannot_claim_market_scope() -> None:
    with pytest.raises(ValidationError, match="only market evidence"):
        ContextAsset(
            ref=ContextAssetRef(
                asset_id="project_evidence_001",
                asset_class=ContextAssetClass.PROJECT_EVIDENCE,
                revision=2,
            ),
            title="Tracing implementation",
            payload={"summary": "Tracing is implemented."},
            market_scope=MarketEvidenceScope.BROAD,
        )


def test_manifest_cannot_authorize_fact_mutation() -> None:
    with pytest.raises(ValidationError):
        ContextManifest(
            manifest_id="context_manifest_001",
            task_type="gap_analysis",
            included=(),
            excluded=(),
            vertical_knowledge_refs=(),
            provider="local-test-provider",
            model_id="test-model",
            capabilities=(),
            skills=(),
            input_hash="a" * 64,
            actor="user",
            run_id="run_001",
            created_at=datetime(2026, 9, 18, tzinfo=UTC),
            authorizes_fact_mutation=True,
        )
