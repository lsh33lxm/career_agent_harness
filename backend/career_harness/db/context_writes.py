from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from career_harness.core.context import ContextManifest
from career_harness.db.models import (
    ContextManifestAssetRefRow,
    ContextManifestKnowledgeRefRow,
    ContextManifestRow,
)


class ContextManifestWrite:
    """Stages one immutable manifest aggregate in the command transaction."""

    def __init__(self, manifest: ContextManifest) -> None:
        self.manifest = manifest

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "context-manifest-write-v1",
            "manifest": self.manifest.model_dump(mode="json", exclude={"created_at"}),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        if entity_revision != 1:
            raise ValueError("context manifests are immutable create-only aggregates")

        manifest_id = self.manifest.manifest_id
        for ordinal, item in enumerate(self.manifest.included):
            session.add(
                ContextManifestAssetRefRow(
                    manifest_id=manifest_id,
                    asset_id=item.ref.asset_id,
                    disposition="included",
                    ordinal=ordinal,
                    asset_class=item.ref.asset_class.value,
                    asset_revision=item.ref.revision,
                    reason=item.reason.value,
                    matched_terms=list(item.matched_terms),
                )
            )
        for ordinal, item in enumerate(self.manifest.excluded):
            session.add(
                ContextManifestAssetRefRow(
                    manifest_id=manifest_id,
                    asset_id=item.ref.asset_id,
                    disposition="excluded",
                    ordinal=ordinal,
                    asset_class=item.ref.asset_class.value,
                    asset_revision=item.ref.revision,
                    reason=item.reason.value,
                    matched_terms=[],
                )
            )
        for ordinal, item in enumerate(self.manifest.vertical_knowledge_refs):
            session.add(
                ContextManifestKnowledgeRefRow(
                    manifest_id=manifest_id,
                    ordinal=ordinal,
                    knowledge_id=item.knowledge_id,
                    knowledge_revision=item.revision,
                )
            )

        # The schema seals and validates the aggregate when the parent is inserted.
        # Flush the deferred-FK children first so the parent count trigger can inspect them.
        session.flush()
        session.add(
            ContextManifestRow(
                manifest_id=manifest_id,
                contract_version=self.manifest.contract_version,
                task_type=self.manifest.task_type,
                selection_policy_version=self.manifest.selection_policy_version,
                compression_policy_version=self.manifest.compression_policy_version,
                provider=self.manifest.provider,
                model_id=self.manifest.model_id,
                capabilities=list(self.manifest.capabilities),
                skills=list(self.manifest.skills),
                input_hash=self.manifest.input_hash,
                actor=self.manifest.actor,
                run_id=self.manifest.run_id,
                created_at=occurred_at,
                included_count=len(self.manifest.included),
                excluded_count=len(self.manifest.excluded),
                knowledge_ref_count=len(self.manifest.vertical_knowledge_refs),
            )
        )
