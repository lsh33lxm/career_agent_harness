from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.context import (
    ContextAssetClass,
    ContextAssetRef,
    ContextManifest,
    ExcludedContextAsset,
    ExclusionReason,
    IncludedContextAsset,
    SelectionReason,
    VerticalKnowledgeRef,
)
from career_harness.db.models import (
    ContextManifestAssetRefRow,
    ContextManifestKnowledgeRefRow,
    ContextManifestRow,
)


class ContextManifestRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, manifest_id: str) -> ContextManifest | None:
        with Session(self.engine) as session:
            row = session.get(ContextManifestRow, manifest_id)
            return self._to_manifest(session, row) if row is not None else None

    def list_for_run(self, run_id: str) -> tuple[ContextManifest, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ContextManifestRow)
                .where(ContextManifestRow.run_id == run_id)
                .order_by(ContextManifestRow.created_at, ContextManifestRow.manifest_id)
            ).all()
            return tuple(self._to_manifest(session, row) for row in rows)

    @staticmethod
    def _to_manifest(session: Session, row: ContextManifestRow) -> ContextManifest:
        included_rows = session.scalars(
            select(ContextManifestAssetRefRow)
            .where(
                ContextManifestAssetRefRow.manifest_id == row.manifest_id,
                ContextManifestAssetRefRow.disposition == "included",
            )
            .order_by(ContextManifestAssetRefRow.ordinal)
        ).all()
        excluded_rows = session.scalars(
            select(ContextManifestAssetRefRow)
            .where(
                ContextManifestAssetRefRow.manifest_id == row.manifest_id,
                ContextManifestAssetRefRow.disposition == "excluded",
            )
            .order_by(ContextManifestAssetRefRow.ordinal)
        ).all()
        knowledge_rows = session.scalars(
            select(ContextManifestKnowledgeRefRow)
            .where(ContextManifestKnowledgeRefRow.manifest_id == row.manifest_id)
            .order_by(ContextManifestKnowledgeRefRow.ordinal)
        ).all()

        included = tuple(
            IncludedContextAsset(
                ref=ContextAssetRef(
                    asset_id=item.asset_id,
                    asset_class=ContextAssetClass(item.asset_class),
                    revision=item.asset_revision,
                ),
                reason=SelectionReason(item.reason),
                matched_terms=tuple(item.matched_terms),
            )
            for item in included_rows
        )
        excluded = tuple(
            ExcludedContextAsset(
                ref=ContextAssetRef(
                    asset_id=item.asset_id,
                    asset_class=ContextAssetClass(item.asset_class),
                    revision=item.asset_revision,
                ),
                reason=ExclusionReason(item.reason),
            )
            for item in excluded_rows
        )
        knowledge = tuple(
            VerticalKnowledgeRef(
                knowledge_id=item.knowledge_id,
                revision=item.knowledge_revision,
            )
            for item in knowledge_rows
        )
        if (len(included), len(excluded), len(knowledge)) != (
            row.included_count,
            row.excluded_count,
            row.knowledge_ref_count,
        ):
            raise RuntimeError("persisted context manifest aggregate is incomplete")

        return ContextManifest(
            manifest_id=row.manifest_id,
            contract_version=row.contract_version,
            task_type=row.task_type,
            included=included,
            excluded=excluded,
            selection_policy_version=row.selection_policy_version,
            compression_policy_version=row.compression_policy_version,
            vertical_knowledge_refs=knowledge,
            provider=row.provider,
            model_id=row.model_id,
            capabilities=tuple(row.capabilities),
            skills=tuple(row.skills),
            input_hash=row.input_hash,
            actor=row.actor,
            run_id=row.run_id,
            created_at=row.created_at,
        )
