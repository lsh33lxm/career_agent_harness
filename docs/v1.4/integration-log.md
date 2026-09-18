# v1.4 Integration Log

No feature branches have been integrated yet.

| Branch | Commit | Modules | Tests | Conflicts | Migration | Follow-up |
| --- | --- | --- | --- | --- | --- | --- |
| `main` baseline | `63ca32f` | v1.4 PRD/Handoff | Read/verified | None | None | Wave 0 contract freeze |
| `codex/v14-opportunity-core` | `e09c9a8` (merge `04bccfa`) | Opportunity admission, Watchlist, priorities | 41 passed, 1 skipped; Ruff passed | None | None | Lead-owned persistence/API; link admitted Opportunity to Job in schema |
| `codex/v14-capability-core` | `5468c52` (merge `cd5728c`) | Official graph, personal overlay, bindings, investment | 57 passed, 1 skipped; Ruff passed | None | None | Lead-owned persistence/API; version heuristic changes |
| `codex/v14-project-evidence-core` | `6df933e` (merge `989fa9e`) | Scan scope, project evidence/state, L1 executor | 72 passed, 1 skipped; Ruff passed | None | None | Lead-owned persistence/API; scanner must enforce resolved-path/reparse safety |
| integration | `3f102f0` | Opportunity relational schema/migration | 75 passed, 1 skipped; Ruff passed; upgrade/downgrade passed | None | Additive 0002 | Typed repository must join revision/event transaction |
| `codex/v14-context-core` | `c294937` (merge `647f45e`) | Context assets, selector, compiler, manifest | 86 passed, 1 skipped; Ruff passed | None | None | Lead-owned persistence/API and `context.compiled` event |

Every feature merge must record branch, reviewed commit, owned modules, commands/results, conflict
resolution, migration impact and remaining follow-up before the integration branch advances.
