# v1.4 Progress

| Work item | Status | Last update | Evidence |
| --- | --- | --- | --- |
| Repository reconnaissance | DONE | 2026-09-18 | `architecture-map.md`; baseline commands run. |
| PRD/Handoff version control | DONE | 2026-09-18 | `main` commit `63ca32f`. |
| Integration branch/worktree | DONE | 2026-09-18 | `refactor/v1.4-integration`. |
| Shared contract freeze | DONE | 2026-09-19 | `158547b`; contract version `0.2.0`. |
| Repository contract alignment | DONE | 2026-09-18 | `32 passed, 1 skipped`; Ruff passed. |
| Additive migration strategy | DONE | 2026-09-18 | `migration-plan.md`; schema unchanged. |
| Wave 1 decomposition/prompts | DONE | 2026-09-18 | `f98faf6`; four prompts, three active worktrees. |
| Wave 1 domain contracts | DONE | 2026-09-18 | Capability, Opportunity, Project Evidence and Context integrated. |
| Wave 1 persistence/integration | IN_PROGRESS | 2026-09-19 | All Wave 1 schemas and Context atomic service done; Project/Capability read paths pending. |
| Opportunity typed persistence | DONE | 2026-09-18 | `3f102f0`; 0002 migration, ORM parity, upgrade/downgrade tests. |
| Atomic Opportunity command path | DONE | 2026-09-18 | `01e2bbe`; typed/generic truth, event and idempotency share one transaction. |
| Opportunity Priority/read repository | DONE | 2026-09-18 | `878d222`; independent priorities and aggregate revisions tested. |
| Opportunity Local API/runtime | DONE | 2026-09-18 | `d1004b2`; auth, idempotency, conflict redaction and bootstrap tested. |
| Capability typed persistence | DONE | 2026-09-18 | `2b7901d`; additive 0003, immutable graph and overlay/binding constraints. |
| Opportunity desktop UI | DONE | 2026-09-18 | `f888f9a`, `c990589`, merge `f37b92b`, layout fix `0cee6c6`; 16 tests/build and desktop/390/320 visual checks passed. |
| Project Evidence typed persistence | DONE | 2026-09-19 | `158547b`; additive 0004, atomic relational basis, authority/scope and upgrade/downgrade tests. |
| Context Manifest typed persistence | DONE | 2026-09-19 | `95d3df6`; additive 0005, ordered immutable refs and metadata-only privacy boundary. |
| Context Manifest atomic service/read | DONE | 2026-09-19 | `6ca47cc`; one transaction, canonical replay, exact ordered readback and compiler-output binding. |
| Project typed reads / safe scanner | IN_PROGRESS | 2026-09-19 | `codex/v14-project-read-scanner`; scoped worktree active. |
| Capability typed read repository | IN_PROGRESS | 2026-09-19 | `codex/v14-capability-read`; scoped worktree active. |

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
- Capability Persistence: `2b7901d`; full pytest `114 passed, 1 skipped`, Ruff passed. Official
  graph releases are immutable and separate from revision-preserving personal overlays.
- Opportunity Desktop: `f888f9a`, `c990589` merged as `f37b92b`, with integration layout fix
  `0cee6c6`; backend `115 passed, 1 skipped`, Ruff passed, frontend `16 passed`, Vite build passed,
  npm audit found 0 vulnerabilities, and desktop/390/320 visual checks passed without overflow.
- Project Evidence Persistence: `158547b`; full pytest `136 passed, 1 skipped`, Ruff passed and
  `0003 -> 0004 -> 0003 -> 0004` rehearsal passed. Canonical capability state and typed basis are
  one deferred-FK transaction; real scanner containment and read repositories remain follow-ups.
- Context Manifest Persistence/Service: `95d3df6`, `6ca47cc`; full pytest `159 passed, 1 skipped`,
  Ruff and format checks passed, and `0004 -> 0005 -> 0004 -> 0005` rehearsal passed. Ordered refs
  and bounded audit metadata are immutable; typed rows, generic revision, event and idempotency are
  atomic; replay returns the first canonical timestamp; compiled content is not stored.

## Baseline verification

- Python: `31 passed, 1 skipped` before Wave 0 edits.
- Ruff: passed before Wave 0 edits.
- Frontend/Rust: last full verified results are in `GOAL_COMPLETION_REPORT.md`; rerun at Wave 0
  close because shared backend-only changes do not touch those surfaces.
