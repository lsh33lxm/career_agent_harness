# v1.4 Integration Log

Feature branches are integrated only after contract and test review; `main` remains unchanged.

| Branch | Commit | Modules | Tests | Conflicts | Migration | Follow-up |
| --- | --- | --- | --- | --- | --- | --- |
| `main` baseline | `63ca32f` | v1.4 PRD/Handoff | Read/verified | None | None | Wave 0 contract freeze |
| `codex/v14-opportunity-core` | `e09c9a8` (merge `04bccfa`) | Opportunity admission, Watchlist, priorities | 41 passed, 1 skipped; Ruff passed | None | None | Lead-owned persistence/API; link admitted Opportunity to Job in schema |
| `codex/v14-capability-core` | `5468c52` (merge `cd5728c`) | Official graph, personal overlay, bindings, investment | 57 passed, 1 skipped; Ruff passed | None | None | Lead-owned persistence/API; version heuristic changes |
| `codex/v14-project-evidence-core` | `6df933e` (merge `989fa9e`) | Scan scope, project evidence/state, L1 executor | 72 passed, 1 skipped; Ruff passed | None | None | Lead-owned persistence/API; scanner must enforce resolved-path/reparse safety |
| integration | `3f102f0` | Opportunity relational schema/migration | 75 passed, 1 skipped; Ruff passed; upgrade/downgrade passed | None | Additive 0002 | Typed repository must join revision/event transaction |
| `codex/v14-context-core` | `c294937` (merge `647f45e`) | Context assets, selector, compiler, manifest | 86 passed, 1 skipped; Ruff passed | None | None | Lead-owned persistence/API and `context.compiled` event |
| integration | `01e2bbe` | Atomic command hook and Opportunity application service | 92 passed, 1 skipped; Ruff passed; rollback/replay passed | None | None | Add typed priority commands and Local API |
| integration | `878d222` | Independent Suggested/User Priority writes and read repository | 97 passed, 1 skipped; Ruff passed | None | None | API/UI projection |
| integration | `d1004b2` | Authenticated Opportunity API and runtime DB bootstrap | 103 passed, 1 skipped; Ruff passed | None | Runtime applies 0001/0002 | Desktop Opportunity UI |
| integration | `2b7901d` | Versioned Capability relational schema | 114 passed, 1 skipped; Ruff passed; upgrade/downgrade passed | None | Additive 0003 | Capability repository/API; Project/Context schema |
| `codex/v14-opportunity-ui` | `f888f9a`, `c990589` (merge `f37b92b`; layout `0cee6c6`) | Authenticated Opportunity desktop workspace and responsive shell | Backend 115 passed, 1 skipped; Ruff passed; frontend 16 passed; build passed; npm audit 0; desktop/390/320 visual checks passed | None | None | Project/Capability read projections after persistence |
| integration | `158547b` | Scoped Project Evidence, relational capability basis and L1 enhancement persistence | 136 passed, 1 skipped; Ruff and diff check passed; `0003 -> 0004 -> 0003 -> 0004` passed | None | Additive 0004 | Realpath/reparse-safe scanner; Project/Capability read repositories and API |
| integration | `95d3df6` | Immutable metadata-only Context Manifest persistence | 151 passed, 1 skipped; Ruff and diff check passed; `0004 -> 0005 -> 0004 -> 0005` passed | None | Additive 0005 | Atomic `context.compiled` command/event write and exact read repository |
| integration | `6ca47cc` | Atomic Context compilation service, typed write and exact read repository | 159 passed, 1 skipped; Ruff, format and diff checks passed; scoped review found no remaining P0/P1 | Compiler-output identity P1 fixed before commit | None | Project Evidence scanner/repository and Capability read paths |
| `codex/v14-capability-read` + integration | `1615581`, `3c2d18c` (merge `7e7dfa5`; Lead fix `61b5a4f`) | Official/personal/market/investment reads; stable personal identity; exact Project Evidence binding contract | 166 passed, 1 skipped; Ruff and diff checks passed; independent review found no P0/P1 | None | Additive 0006; downgrade/re-upgrade passed | Match/Gap service and required API projection |
| `codex/v14-project-read-scanner` | `116fd50`, `f3cfd9e` (merge `44a3e00`) | Canonical Project/scope reads; POSIX/Windows handle-anchored scanner | 192 passed, 3 skipped; Ruff and diff checks passed; P1 drive allowlist fixed before merge | None | None | Review exact Project revision pin on manifest before any schema change |

Every feature merge must record branch, reviewed commit, owned modules, commands/results, conflict
resolution, migration impact and remaining follow-up before the integration branch advances.
