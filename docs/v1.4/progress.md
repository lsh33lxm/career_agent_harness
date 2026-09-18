# v1.4 Progress

| Work item | Status | Last update | Evidence |
| --- | --- | --- | --- |
| Repository reconnaissance | DONE | 2026-09-18 | `architecture-map.md`; baseline commands run. |
| PRD/Handoff version control | DONE | 2026-09-18 | `main` commit `63ca32f`. |
| Integration branch/worktree | DONE | 2026-09-18 | `refactor/v1.4-integration`. |
| Shared contract freeze | DONE | 2026-09-18 | `75f973b`; contract version `0.1.0`. |
| Repository contract alignment | DONE | 2026-09-18 | `32 passed, 1 skipped`; Ruff passed. |
| Additive migration strategy | DONE | 2026-09-18 | `migration-plan.md`; schema unchanged. |
| Wave 1 decomposition/prompts | DONE | 2026-09-18 | `f98faf6`; four prompts, three active worktrees. |
| Wave 1 domain contracts | DONE | 2026-09-18 | Capability, Opportunity, Project Evidence and Context integrated. |
| Wave 1 persistence/integration | IN_PROGRESS | 2026-09-18 | Opportunity schema done; atomic typed repository/API pending. |
| Opportunity typed persistence | DONE | 2026-09-18 | `3f102f0`; 0002 migration, ORM parity, upgrade/downgrade tests. |
| Atomic Opportunity command path | DONE | 2026-09-18 | `01e2bbe`; typed/generic truth, event and idempotency share one transaction. |
| Opportunity Priority/read repository | DONE | 2026-09-18 | `878d222`; independent priorities and aggregate revisions tested. |
| Opportunity Local API/runtime | DONE | 2026-09-18 | `d1004b2`; auth, idempotency, conflict redaction and bootstrap tested. |

## Integrated workstreams

- Opportunity Core: `e09c9a8` merged as `04bccfa`; integration pytest `41 passed, 1 skipped`,
  Ruff passed. Persistence/API follow-up remains Lead-owned.
- Capability Core: `5468c52` merged as `cd5728c`; combined pytest `57 passed, 1 skipped`,
  Ruff passed. Persistence/API and heuristic versioning remain Lead-owned.
- Project Evidence Core: `6df933e` merged as `989fa9e`; combined pytest `72 passed, 1 skipped`,
  Ruff passed. Real scanner resolved-path enforcement remains a follow-up.
- Opportunity Persistence: `3f102f0`; full pytest `75 passed, 1 skipped`, Ruff passed. No legacy
  conversion or production database write occurred.
- Context Core: `c294937` merged as `647f45e`; combined pytest `86 passed, 1 skipped`, Ruff passed.
  Empty relevance selects no context and manifests cannot authorize fact mutation.
- Atomic Opportunity Service: `01e2bbe`; full pytest `92 passed, 1 skipped`, Ruff passed. Hook
  failure rollback, replay and changed typed input conflict are covered.
- Priority/Read/API: `878d222`, `d1004b2`; full pytest `103 passed, 1 skipped`, Ruff passed.
  Manual and Agent-proposal/user-confirmation admissions are available through authenticated API.

## Baseline verification

- Python: `31 passed, 1 skipped` before Wave 0 edits.
- Ruff: passed before Wave 0 edits.
- Frontend/Rust: last full verified results are in `GOAL_COMPLETION_REPORT.md`; rerun at Wave 0
  close because shared backend-only changes do not touch those surfaces.
