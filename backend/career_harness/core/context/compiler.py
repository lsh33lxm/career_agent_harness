from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from career_harness.core.common import utc_now
from career_harness.core.context.models import (
    COMPRESSION_POLICY_VERSION,
    SELECTION_POLICY_VERSION,
    CompiledContext,
    ContextAsset,
    ContextCompilationRequest,
    ContextManifest,
    ContextSelectionResult,
    ExcludedContextAsset,
    ExclusionReason,
    IncludedContextAsset,
    SelectionReason,
)


class RelevanceSelector(Protocol):
    def select(self, request: ContextCompilationRequest) -> ContextSelectionResult: ...


class ContextCompilerPort(Protocol):
    def compile(self, request: ContextCompilationRequest) -> CompiledContext: ...


class DeterministicRelevanceSelector:
    def select(self, request: ContextCompilationRequest) -> ContextSelectionResult:
        allowed_classes = set(request.allowed_asset_classes)
        explicit_ids = set(request.explicit_asset_ids)
        requested_terms = set(request.relevance_terms)
        ranked: list[tuple[int, int, ContextAsset, IncludedContextAsset]] = []
        excluded: list[ExcludedContextAsset] = []

        for asset in request.candidates:
            if asset.ref.asset_class not in allowed_classes:
                excluded.append(
                    ExcludedContextAsset(
                        ref=asset.ref,
                        reason=ExclusionReason.ASSET_CLASS_NOT_ALLOWED,
                    )
                )
                continue

            if asset.ref.asset_id in explicit_ids:
                ranked.append(
                    (
                        1,
                        0,
                        asset,
                        IncludedContextAsset(
                            ref=asset.ref,
                            reason=SelectionReason.EXPLICIT_REFERENCE,
                        ),
                    )
                )
                continue

            matched_terms = tuple(sorted(requested_terms & set(asset.relevance_terms)))
            if not matched_terms:
                excluded.append(
                    ExcludedContextAsset(
                        ref=asset.ref,
                        reason=ExclusionReason.NO_RELEVANCE_MATCH,
                    )
                )
                continue

            ranked.append(
                (
                    0,
                    len(matched_terms),
                    asset,
                    IncludedContextAsset(
                        ref=asset.ref,
                        reason=SelectionReason.RELEVANCE_TERM_MATCH,
                        matched_terms=matched_terms,
                    ),
                )
            )

        ranked.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                item[2].ref.asset_class.value,
                item[2].ref.asset_id,
                item[2].ref.revision,
            )
        )
        selected = ranked[: request.max_assets]
        excluded.extend(
            ExcludedContextAsset(
                ref=asset.ref,
                reason=ExclusionReason.SELECTION_LIMIT,
            )
            for _, _, asset, _ in ranked[request.max_assets :]
        )
        excluded.sort(
            key=lambda item: (
                item.ref.asset_class.value,
                item.ref.asset_id,
                item.ref.revision,
            )
        )
        return ContextSelectionResult(
            included=tuple(item[3] for item in selected),
            excluded=tuple(excluded),
        )


def context_input_hash(
    request: ContextCompilationRequest,
    selected_assets: tuple[ContextAsset, ...],
) -> str:
    knowledge = tuple(
        sorted(
            request.vertical_knowledge,
            key=lambda item: (item.ref.knowledge_id, item.ref.revision),
        )
    )
    hash_input = {
        "task_type": request.task_type,
        "task_input": request.task_input,
        "assets": [asset.model_dump(mode="json") for asset in selected_assets],
        "vertical_knowledge": [asset.model_dump(mode="json") for asset in knowledge],
        "capabilities": sorted(request.capabilities),
        "skills": sorted(request.skills),
        "selection_policy_version": SELECTION_POLICY_VERSION,
        "compression_policy_version": COMPRESSION_POLICY_VERSION,
    }
    encoded = json.dumps(
        hash_input,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class BasicContextCompiler:
    def __init__(
        self,
        selector: RelevanceSelector | None = None,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._selector = selector or DeterministicRelevanceSelector()
        self._clock = clock

    def compile(self, request: ContextCompilationRequest) -> CompiledContext:
        selection = self._selector.select(request)
        assets_by_id = {asset.ref.asset_id: asset for asset in request.candidates}
        dispositions = selection.included + selection.excluded
        disposition_ids = {item.ref.asset_id for item in dispositions}
        if disposition_ids != set(assets_by_id) or len(dispositions) != len(assets_by_id):
            raise ValueError("selector must give every context candidate exactly one disposition")
        if any(assets_by_id[item.ref.asset_id].ref != item.ref for item in dispositions):
            raise ValueError(
                "selector dispositions must preserve candidate references and revisions"
            )
        selected_assets = tuple(assets_by_id[item.ref.asset_id] for item in selection.included)
        knowledge = tuple(
            sorted(
                request.vertical_knowledge,
                key=lambda item: (item.ref.knowledge_id, item.ref.revision),
            )
        )
        manifest = ContextManifest(
            manifest_id=request.manifest_id,
            task_type=request.task_type,
            included=selection.included,
            excluded=selection.excluded,
            vertical_knowledge_refs=tuple(item.ref for item in knowledge),
            provider=request.provider,
            model_id=request.model_id,
            capabilities=request.capabilities,
            skills=request.skills,
            input_hash=context_input_hash(request, selected_assets),
            actor=request.actor,
            run_id=request.run_id,
            created_at=self._clock(),
        )
        return CompiledContext(
            task_type=request.task_type,
            task_input=request.task_input,
            assets=selected_assets,
            vertical_knowledge=knowledge,
            manifest=manifest,
        )
