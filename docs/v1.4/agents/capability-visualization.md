# Scoped Agent Task: Capability Workspace Visualization

## Role

Implementation engineer for one bounded PRD v1.4 P1 slice. Do not act as architecture owner or
merge owner.

## Goal

Implement the candidate-scoped Capability Workspace derived read model, authenticated Local API
and responsive desktop visualization defined by contract `v1.4-contract-0.13.0` and D-023.

## Repository

`D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness`

## Worktree

`D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\capability-visualization`

## Branch

`codex/v14-capability-visualization`

## Base Commit

`709c2dd` (`docs: freeze capability workspace contract 0.13.0`)

## Workstream

`W2-CAP-VIZ`

## Task

1. Add typed immutable Capability Workspace projection models and a deterministic pure assembler.
2. Add only the minimum typed repository list reads required to assemble one explicit candidate's
   latest personal states and existing exact bindings/investment proposals.
3. Add a read-only service and authenticated `GET /api/v1/capabilities/{candidate_id}` endpoint,
   with optional exact `graph_version_id` selection and empty projection when no graph exists.
4. Wire the endpoint into both test app construction and the real runtime app.
5. Replace the desktop `/capabilities` placeholder with a responsive, inspectable visualization
   that renders Core ordering/data without recomputing business scores. Provide an explicit
   candidate selector/input because identity must never be guessed. Use Lucide icons already in the
   app and preserve existing shell/design conventions.
6. Add focused unit, integration/API and frontend tests, including zero-write behavior and narrow
   viewport layout-safe states.

## Why This Task Exists

The official graph, personal overlay, evidence/market bindings, InvestmentState and Broad Market
Trend are implemented but invisible in the product. Joining them in React would move business
semantics into a client and could mix candidate identity or market authority. Core must compose the
read model; the desktop only visualizes it.

## Required Reading

```text
AGENTS.md
docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md sections 9-14, 23.4, 28.5, 29
docs/v1.4/contracts.md (0.13.0 Capability workspace read model)
docs/v1.4/decision-log.md (D-023, plus D-007/D-010/D-022)
backend/career_harness/core/capability/models.py
backend/career_harness/core/market/trend.py
backend/career_harness/db/capability_repository.py
backend/career_harness/services/market_trend_service.py
backend/career_harness/api/app.py
backend/career_harness/api/runtime.py
backend/career_harness/api/today.py
apps/desktop/src/app/App.tsx
apps/desktop/src/pages/OpportunitiesPage.tsx
apps/desktop/src/api/client.ts
apps/desktop/src/styles.css
```

## Relevant Source Files

```text
backend/career_harness/db/models.py
tests/integration/test_capability_repository.py
tests/integration/test_today_api.py
tests/integration/test_runtime_app.py
apps/desktop/src/pages/TodayPage.tsx
apps/desktop/src/pages/TodayPage.test.tsx
```

## Owned Paths

```text
backend/career_harness/core/capability_workspace/                # new, if useful
backend/career_harness/db/capability_repository.py                # narrow list reads only
backend/career_harness/services/capability_workspace_service.py   # new
backend/career_harness/api/capabilities.py                        # new
backend/career_harness/api/app.py
backend/career_harness/api/runtime.py
backend/career_harness/services/__init__.py                       # only if export needed
apps/desktop/src/api/capabilities.ts                              # new
apps/desktop/src/api/useCapabilities.ts                           # new, if useful
apps/desktop/src/pages/CapabilitiesPage.tsx                       # new
apps/desktop/src/app/App.tsx
apps/desktop/src/styles.css                                       # scoped capability styles only
tests/unit/test_capability_workspace.py                           # new
tests/integration/test_capability_workspace_service.py            # new
tests/integration/test_capability_api.py                          # new
tests/integration/test_runtime_app.py                             # narrow wiring assertion
apps/desktop/src/pages/CapabilitiesPage.test.tsx                  # new
apps/desktop/src/api/capabilities.test.ts                         # new, if useful
```

## Read-only Paths

```text
docs/
backend/career_harness/core/capability/models.py
backend/career_harness/core/market/
backend/career_harness/db/models.py
backend/career_harness/services/market_trend_service.py
all existing migrations
```

## Forbidden Paths

```text
migrations/
legacy importers and D:\0.小红书投稿\小红书稿\9.15 三期\agent_rader
main or refactor/v1.4-integration branches
runtime databases, credentials, browser profiles or generated artifacts
```

## Shared Contract Version

`v1.4-contract-0.13.0`; D-023. No competing representation. If required fields or semantics are
missing, stop and return `CONTRACT CHANGE REQUEST`.

## Dependencies

Capability repository/graph/overlay reads, Broad Market Trend 0.12.0, authenticated Local API and
existing React AppShell are integrated at base `709c2dd`.

## Business Invariants

- Evidence != Fact != Signal != Decision != Outcome.
- Official graph != Personal Capability Overlay.
- Project presence != Personal mastery.
- TARGET demand remains distinct from BROAD trend.
- InvestmentState is a proposal, not a decision or UserPriority.
- Candidate identity is explicit; never combine or guess identities.
- Missing personal state stays absent.
- Same canonical inputs produce the same business projection.
- Service/API are read-only and perform zero canonical writes.
- React owns layout/selection only, never business ranking or derived truth.

## Implementation Requirements

- Prefer existing Pydantic frozen models and repository conversion patterns.
- Select one graph version exactly once per request. Reject unknown explicit graph versions with a
  clear 404 or typed service error; no latest substitution for an explicit ref.
- Keep stable ordering independent of database return order.
- Input revisions must include every used graph version, personal state revision, evidence binding,
  market binding and investment state identity without conflating their kinds.
- Latest personal/investment selection must be deterministic and tested.
- Empty database returns an explicit empty workspace, not fabricated example data.
- UI must have loading, error, retry, empty-graph, graph-without-overlay and populated states.
- UI must remain usable at 320/390 px and desktop widths with no incoherent overlap or horizontal
  page overflow. Use semantic buttons/inputs and accessible selected-node detail.
- No new network destinations, analytics, telemetry or persistence.

## Testing

Use the root repository environment:

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest tests/unit/test_capability_workspace.py tests/integration/test_capability_workspace_service.py tests/integration/test_capability_api.py tests/integration/test_runtime_app.py -q
& $ruff check backend tests
& $ruff format --check <changed Python files>
npm --prefix apps/desktop test -- --run
npm --prefix apps/desktop run build
git diff --check
```

Do not run broad formatting. Three known Windows symlink skips are non-blocking only in the full
suite. Report actual results; never fabricate them.

## Definition of Done

- Contract 0.13.0 is implemented without migration or writes.
- Candidate scope, exact graph selection, separation of target/broad/personal/investment data and
  deterministic input refs are tested.
- Authenticated API and runtime wiring are tested.
- Capability page replaces only its placeholder and handles all expected states responsively.
- Focused Python tests, frontend tests/build, Ruff, changed-file format and diff checks pass.
- Diff is self-reviewed and contains no unrelated changes.

## Commit Requirements

Use explicit `git add <files>` only; never `git add .`. Commit to
`codex/v14-capability-visualization` with a focused message such as
`feat: add capability workspace visualization`. Do not merge, rebase, push or modify integration.

## Final Report

Return: summary, exact commit, changed files, tests/commands/results, security/data impact, known
limitations and any `CONTRACT CHANGE REQUEST`. Do not claim integration or release completion.
