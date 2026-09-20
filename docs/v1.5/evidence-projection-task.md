# Evidence provenance read projection

Scope authorized by overnight C/D: consume existing evidence tables only. No new
domain semantics or promotion; shared archive authority remains contract 0.17.0.

- Add bounded deterministic EvidenceRepository list/page reads ordered by evidence
  ref ID, resolving each exact Source/Snapshot/Artifact chain through existing get.
  Dangling/mismatched provenance fails loud. Pagination must expose whether more
  results exist, not imply the first page is a total population.
- Add bearer-authenticated GET /api/v1/evidence list and exact reference detail.
  Metadata only: existing typed provenance DTO. No artifact byte/file download,
  legacy filesystem read, source URL fetch or write endpoint. Reuse runtime engine.
- Add /history/evidence under History; use shared Guangfu tokens. Display source
  type, historical locator, artifact hash/size/class, exact snapshot/ref and capture
  time. Explain preservation is not claim confirmation. No personal mastery/fact
  claims. Keep missing/error/loading explicit and links inert text (no local file URI).
- Normal Core DB shows its own records; a separately launched rehearsal runtime
  exposes rehearsal evidence only. Do not change production DB/config or silently
  union staging with canonical records. Label legacy_historical_unconfirmed entries.
- Tests: auth, pagination stability, missing/dangling provenance, no mutation route;
  frontend empty/error/retry/detail and 320px long IDs. Existing API validation applies.
- Owned: new evidence API/client/page/tests, EvidenceRepository additive reads,
  app/runtime wiring, App.tsx route and HistoryPage link; no shared contracts/schema.
  Separate worktree, focused checks, commit, independent review before merge.
