# Read-only Review: Capability Workspace Visualization

## Role

Independent senior reviewer. Read-only: do not edit, format, commit, merge, rebase or push.

## Goal

Review `ae39eb6` against base `f2727cf`, contract `v1.4-contract-0.13.0`, D-023 and the scoped
implementation prompt. Find concrete bugs, security/privacy violations, contract drift, regressions
and missing tests before integration.

## Repository / Worktree / Branch

```text
Repository: D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
Feature worktree: D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\capability-visualization
Branch: codex/v14-capability-visualization
Base: f2727cf
Reviewed commit: ae39eb6
Workstream: W2-CAP-VIZ
```

## Required Reading

```text
AGENTS.md
docs/v1.4/contracts.md (0.13.0 Capability workspace read model)
docs/v1.4/decision-log.md (D-023, D-007, D-010, D-022)
docs/v1.4/agents/capability-visualization.md
git diff f2727cf..ae39eb6
```

## Review Scope

All 18 files changed by `ae39eb6`. Existing files outside the diff are read-only context.

## Contract / Business Checks

- Exactly one explicit candidate identity; no cross-candidate data or guessed identity.
- Explicit graph versions resolve exactly and fail clearly; latest is selected only when omitted.
- Official graph, personal state, evidence, TARGET/BROAD market and InvestmentState proposal remain
  semantically separate.
- Missing overlay/investment stays absent; project presence cannot imply mastery.
- Stable ordering and complete typed input revision refs are deterministic.
- Empty database returns an explicit empty workspace.
- Service/API perform zero writes and add no external network/telemetry/credential behavior.
- Client renders Core data and never recomputes business scores/ranking/truth.

## Technical Checks

- Repository latest-selection queries are deterministic and cannot return multiple revisions for
  one identity/capability.
- Pydantic validation prevents malformed, duplicate or dangling projection contents.
- FastAPI dependency/wiring is authenticated, typed and included in the real runtime app.
- Error mapping does not leak sensitive data and distinguishes unknown explicit graph refs.
- React request encoding, abort/retry behavior, empty/error/loading/populated states and selection
  accessibility are correct.
- CSS has stable dimensions, no nested-card misuse, and no 320/390 px overlap/overflow risk.
- Tests exercise cross-candidate isolation, explicit graph behavior, input refs, deterministic
  reordering, zero writes, API auth/runtime wiring and frontend states.

## Commands

Run any focused read-only tests needed to verify findings, using the root `.venv`. Do not run
formatters that write files. Do not claim results you did not observe.

## Output

Findings first, ordered by severity, each with file and line reference, impact and minimum fix:

```text
P0
P1
P2
P3

VERDICT: APPROVE | APPROVE WITH FIXES | REJECT
```

If a severity has no findings, say `None`. Mention residual test gaps even when approving.
