"""Offline projection preview; no Feishu client, credentials or side effects."""

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.today import TodayItem, TodayQueue, TodaySourceRef

MAX_PREVIEW_ROWS = 1000
MAX_PREVIEW_BYTES = 5 * 1024 * 1024


class FeishuTodayRow(FrozenModel):
    ordinal: int = Field(ge=1)
    item: TodayItem


class FeishuTodayPreview(FrozenModel):
    schema_version: Literal["feishu-today-preview-v1"] = "feishu-today-preview-v1"
    mode: Literal["dry_run"] = "dry_run"
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    generated_at: datetime
    policy_version: str
    input_revisions: tuple[TodaySourceRef, ...]
    rows: tuple[FeishuTodayRow, ...]

    def to_json_bytes(self) -> bytes:
        return _json_bytes(self.model_dump(mode="json"))


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def prepare_today_projection(queue: TodayQueue) -> FeishuTodayPreview:
    # Revalidate even a model_copy/model_construct input before preparing the preview.
    verified = TodayQueue.model_validate(queue.model_dump(mode="json"))
    if len(verified.items) > MAX_PREVIEW_ROWS:
        raise ValueError("Today projection exceeds row limit")
    source_bytes = _json_bytes(verified.model_dump(mode="json"))
    if len(source_bytes) > MAX_PREVIEW_BYTES:
        raise ValueError("Today projection exceeds byte limit")
    refs = {(ref.kind, ref.entity_id, ref.revision) for ref in verified.input_revisions}
    for item in verified.items:
        if any((ref.kind, ref.entity_id, ref.revision) not in refs for ref in item.source_refs):
            raise ValueError("Today projection source is absent from exact input revisions")
    preview = FeishuTodayPreview(
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        generated_at=verified.generated_at,
        policy_version=verified.policy_version,
        input_revisions=verified.input_revisions,
        rows=tuple(
            FeishuTodayRow(ordinal=n, item=item) for n, item in enumerate(verified.items, 1)
        ),
    )
    if len(preview.to_json_bytes()) > MAX_PREVIEW_BYTES:
        raise ValueError("Today projection exceeds byte limit")
    return preview
