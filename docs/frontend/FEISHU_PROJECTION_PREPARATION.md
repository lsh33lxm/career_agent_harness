# Feishu projection preparation

Implemented: a pure offline Today projection preview in
`backend/career_harness/adapters/feishu_projection.py`. Input is the existing Core
TodayQueue. Output schema is `schemas/feishu_today_preview.schema.json`. The preview
is deterministic JSON, not an SDK request or synchronization acknowledgement.

| Proposed Feishu field | Preview source | Type / meaning |
| --- | --- | --- |
| Projection key | rows[].item.item_id | Text; stable key, never a Feishu-owned career identity |
| Order | rows[].ordinal | Number; retain Core order |
| Kind | rows[].item.kind | Text |
| User priority | rows[].item.user_priority | Nullable text; user decision, not editable through this adapter |
| Suggested priority | rows[].item.suggested_priority | Nullable text; system suggestion |
| Reasons | rows[].item.reasons | JSON text, code + explanation retained |
| Exact references | rows[].item.source_refs | JSON text, kind/ID/revision retained |
| Deadline / Interview | corresponding item timestamps | ISO text; do not infer timezone or completion |
| Source digest | source_sha256 | SHA-256 of canonical serialized complete input |
| Data time / policy | generated_at / policy_version | Exact source read-model metadata |

Every item ref must occur in input_revisions. Older and current revisions of the same
Application may both be legitimate and remain separate. Limit: 1000 rows / 5 MiB;
overflow fails, never truncates. Preview does not write files itself and cannot write
Core, update priorities, accept proposals or promote evidence. A local caller may
save its bytes to an explicitly selected private output path.

NOT IMPLEMENTED: credential lookup, Feishu table creation, remote upsert/delete,
inbound edits, conflict resolution, retry/outbox delivery and live compatibility
testing. External writes are BLOCKED_EXTERNAL_ACTION until credentials/permission
and a reviewed synchronization contract exist. Old Feishu remains historical
projection reference; it is not canonical. Legacy statistics export will need a
separately resolved staging/authority mapping and is not implied by this Today preview.
