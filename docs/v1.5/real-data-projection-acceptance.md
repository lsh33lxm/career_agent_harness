# Real-data Evidence projection acceptance

Date: 2026-09-20T18:06:03.128069+00:00

Result: PASS. Read-only HTTP projection of the existing restored legacy rehearsal DB;
no canonical cutover, no production DB operation, no legacy filesystem reads, no artifact
content downloads and no migration/bootstrap call. No temporary DB copy was needed.

## Verified results

- Evidence references: 2205; unique IDs: 2205.
- API pages: 23, requested limit 100; strictly sorted cursor traversal,
  no omissions/duplicates; final cursor null.
- Exact detail requests: 2205, all HTTP 200 and equal to the matching list DTO.
- Both list and detail without authorization: HTTP 401.
- Every reference matched the read-only SQL join for exact snapshot, artifact, source,
  digest, byte length, classification, source type, historical locator and selector.
- Every source is `legacy_historical_unconfirmed`; preservation is not fact confirmation.
- Source types: `{"legacy_historical_unconfirmed": 2205}`.
- Artifact classifications across references: `{"personal": 1, "sensitive": 2204}`.
- Before/after row counts (identical): `{"evidence_artifact": 1141, "evidence_ref": 2205, "evidence_source": 2205, "source_snapshot": 2205}`.
- SQLite integrity check: ok; foreign-key violations: 0, before and after.
- Database SHA-256 before: `825b6309e9d4fc2c38072e859006cee7d236f09c7c58d7a96f78cfb827f1252d`.
- Database SHA-256 after: `825b6309e9d4fc2c38072e859006cee7d236f09c7c58d7a96f78cfb827f1252d` (identical).

## Reproduction logic and boundary

Resolve `AppPaths`' existing Data Root and verify the named
`backups/legacy-20260921-rehearsal/restored.rehearsal.db` exists. Open it using SQLite
URI `mode=ro` (including the SQLAlchemy engine creator). Build
`create_app(Settings.for_test(...), evidence_api=EvidenceApi(EvidenceRepository(engine)))`;
use `httpx.ASGITransport`, not `create_runtime_app`. Read `/api/v1/evidence?limit=100`,
follow each returned `next_cursor` as `after`, and request `/api/v1/evidence/{exact_ref_id}`
for every item. Compare each DTO with the existing four-table read-only join. Recompute
DB SHA-256 and counts after closing the engine. The invocation was a local temporary
Python script with the integration `backend` first on `sys.path`, using the repository venv.

This accepts the backend read projection against real rehearsal metadata. Browser
responsive/interaction validation is separate and used synthetic metadata. It does not
claim canonical migration, actual artifact interpretation, personal career truth, or
external Feishu writes. No source path listing or source content is included here.
