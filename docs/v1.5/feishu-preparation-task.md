# Feishu offline projection preparation

Scope: pure export of an existing Core TodayQueue, with schema/mapping and tests.
This is an adapter, not a new domain or approval policy. Existing Today contract/order,
exact references and SuggestedPriority/UserPriority separation remain authoritative.

- Deterministic JSON envelope pins complete input hash, generated_at, policy_version,
  exact input revisions and ordered rows. Each row retains item ID, kind, ordinal,
  reasons, source refs, independent priorities and original times.
- Reject a row source ref absent from queue input revisions, duplicate/conflicting
  input identities and oversized queues; no substitution with latest references.
- Pure transformation: no filesystem, network, secrets, subprocess, outbox writes,
  Feishu SDK, table IDs or production action. Export is a dry-run preview only.
- Include a JSON schema and documented Feishu field mapping with stable projection
  key. No record creation/update/deletion/synchronization is implemented by preview.
  Inbound edits never mutate Core through this adapter.
- Test deterministic bytes/hash, priority separation, no source mutation, missing
  provenance, empty queue and size bounds. Existing Core order must survive export.
- Future external writes are BLOCKED_EXTERNAL_ACTION pending credential/permission
  and a separately reviewed sync contract. JSON schema validity is not live Feishu
  compatibility or successful synchronization.
