from datetime import UTC, datetime

import pytest

from career_harness.core.context import (
    BasicContextCompiler,
    ContextAsset,
    ContextAssetClass,
    ContextAssetRef,
    ContextCompilationRequest,
    ContextSelectionResult,
    ExclusionReason,
    MarketEvidenceScope,
    SelectionReason,
    VerticalKnowledgeAsset,
    VerticalKnowledgeRef,
)

ALL_ASSET_CLASSES = tuple(ContextAssetClass)


def asset(
    asset_id: str,
    asset_class: ContextAssetClass,
    *,
    revision: int = 1,
    terms: tuple[str, ...] = (),
    value: str | None = None,
) -> ContextAsset:
    market_scope = (
        MarketEvidenceScope.TARGET
        if asset_class is ContextAssetClass.MARKET_EVIDENCE
        else None
    )
    return ContextAsset(
        ref=ContextAssetRef(
            asset_id=asset_id,
            asset_class=asset_class,
            revision=revision,
        ),
        title=asset_id,
        payload={"value": value or asset_id},
        relevance_terms=terms,
        market_scope=market_scope,
    )


def request(
    candidates: tuple[ContextAsset, ...],
    **overrides: object,
) -> ContextCompilationRequest:
    values: dict[str, object] = {
        "manifest_id": "context_manifest_001",
        "task_type": "opportunity_gap_analysis",
        "task_input": {"opportunity_id": "opportunity_001"},
        "candidates": candidates,
        "allowed_asset_classes": ALL_ASSET_CLASSES,
        "relevance_terms": ("observability",),
        "provider": "local-test-provider",
        "model_id": "test-model",
        "capabilities": ("structured_generation",),
        "skills": ("gap_analysis",),
        "actor": "user",
        "run_id": "run_001",
    }
    values.update(overrides)
    return ContextCompilationRequest(**values)


def five_assets() -> tuple[ContextAsset, ...]:
    return (
        asset(
            "personal_context_001",
            ContextAssetClass.PERSONAL_CONTEXT,
            revision=3,
            terms=("agent engineering",),
        ),
        asset(
            "career_state_001",
            ContextAssetClass.CAREER_STATE,
            revision=4,
            terms=("deadline",),
        ),
        asset(
            "project_evidence_001",
            ContextAssetClass.PROJECT_EVIDENCE,
            revision=2,
            terms=("observability", "python"),
        ),
        asset(
            "market_evidence_001",
            ContextAssetClass.MARKET_EVIDENCE,
            revision=5,
            terms=("observability",),
        ),
        asset(
            "career_outcome_001",
            ContextAssetClass.CAREER_HISTORY_OUTCOME,
            revision=1,
            terms=("interview",),
        ),
    )


def test_selector_uses_explicit_refs_and_relevance_with_a_deterministic_limit() -> None:
    compiled = BasicContextCompiler().compile(
        request(
            five_assets(),
            explicit_asset_ids=("personal_context_001",),
            max_assets=2,
        )
    )

    assert [item.ref.asset_id for item in compiled.manifest.included] == [
        "personal_context_001",
        "market_evidence_001",
    ]
    assert compiled.manifest.included[0].reason is SelectionReason.EXPLICIT_REFERENCE
    assert compiled.manifest.included[1].reason is SelectionReason.RELEVANCE_TERM_MATCH
    assert compiled.manifest.included[1].matched_terms == ("observability",)

    exclusions = {
        item.ref.asset_id: item.reason for item in compiled.manifest.excluded
    }
    assert exclusions == {
        "career_outcome_001": ExclusionReason.NO_RELEVANCE_MATCH,
        "career_state_001": ExclusionReason.NO_RELEVANCE_MATCH,
        "project_evidence_001": ExclusionReason.SELECTION_LIMIT,
    }


def test_asset_class_boundary_records_an_explicit_exclusion() -> None:
    compiled = BasicContextCompiler().compile(
        request(
            five_assets(),
            allowed_asset_classes=(ContextAssetClass.PROJECT_EVIDENCE,),
            max_assets=5,
        )
    )

    assert [asset.ref.asset_id for asset in compiled.assets] == ["project_evidence_001"]
    excluded = {item.ref.asset_id: item.reason for item in compiled.manifest.excluded}
    assert excluded["market_evidence_001"] is ExclusionReason.ASSET_CLASS_NOT_ALLOWED
    assert excluded["personal_context_001"] is ExclusionReason.ASSET_CLASS_NOT_ALLOWED


def test_empty_relevance_does_not_default_to_all_context() -> None:
    compiled = BasicContextCompiler().compile(
        request(five_assets(), relevance_terms=(), explicit_asset_ids=())
    )

    assert compiled.assets == ()
    assert compiled.manifest.included == ()
    assert len(compiled.manifest.excluded) == 5
    assert {item.reason for item in compiled.manifest.excluded} == {
        ExclusionReason.NO_RELEVANCE_MATCH
    }


def test_input_hash_is_stable_across_candidate_order_and_audit_metadata() -> None:
    candidates = five_assets()
    first = BasicContextCompiler(
        clock=lambda: datetime(2026, 9, 18, 8, tzinfo=UTC)
    ).compile(request(candidates, run_id="run_001", manifest_id="manifest_001"))
    second = BasicContextCompiler(
        clock=lambda: datetime(2026, 9, 19, 9, tzinfo=UTC)
    ).compile(
        request(
            tuple(reversed(candidates)),
            run_id="run_002",
            manifest_id="manifest_002",
        )
    )

    assert first.manifest.input_hash == second.manifest.input_hash
    assert first.manifest.created_at != second.manifest.created_at
    assert first.manifest.run_id != second.manifest.run_id


def test_input_hash_changes_when_selected_payload_changes() -> None:
    original = asset(
        "project_evidence_001",
        ContextAssetClass.PROJECT_EVIDENCE,
        terms=("observability",),
        value="logging only",
    )
    changed = asset(
        "project_evidence_001",
        ContextAssetClass.PROJECT_EVIDENCE,
        terms=("observability",),
        value="logging and tracing",
    )

    first = BasicContextCompiler().compile(request((original,)))
    second = BasicContextCompiler().compile(request((changed,)))

    assert first.manifest.input_hash != second.manifest.input_hash


def test_manifest_records_knowledge_model_capability_actor_and_run() -> None:
    knowledge = VerticalKnowledgeAsset(
        ref=VerticalKnowledgeRef(knowledge_id="knowledge_agent_roles", revision=7),
        payload={"rule": "Project presence does not prove user mastery."},
    )
    compiled = BasicContextCompiler().compile(
        request(five_assets(), vertical_knowledge=(knowledge,))
    )

    manifest = compiled.manifest
    assert manifest.vertical_knowledge_refs == (knowledge.ref,)
    assert manifest.provider == "local-test-provider"
    assert manifest.model_id == "test-model"
    assert manifest.capabilities == ("structured_generation",)
    assert manifest.skills == ("gap_analysis",)
    assert manifest.actor == "user"
    assert manifest.run_id == "run_001"
    assert manifest.authorizes_fact_mutation is False
    assert len(manifest.input_hash) == 64


def test_compiler_rejects_a_selector_that_omits_manifest_dispositions() -> None:
    class IncompleteSelector:
        def select(self, request: ContextCompilationRequest) -> ContextSelectionResult:
            return ContextSelectionResult(included=(), excluded=())

    compiler = BasicContextCompiler(selector=IncompleteSelector())

    with pytest.raises(ValueError, match="every context candidate"):
        compiler.compile(request(five_assets()))
