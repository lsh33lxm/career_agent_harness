# Scoped Agent Task: Today Interview Schedule Inputs

## Role / Goal
Implement W2-TODAY-INTERVIEW only, under frozen contract `v1.4-contract-0.14.0` / D-024.
Fill the missing canonical schedule dimension of existing Today interview-stage items.

## Base / Branch / Worktree
- Base: `dd4dac7` (contract freeze; task-doc commit may also be present).
- Branch: `codex/v14-today-interview`
- Worktree: sibling `agent-career-harness-worktrees/today-interview`
- Integration/main and legacy `agent_rader` are forbidden write targets.

## Required reading
AGENTS.md; STATUS.md; PRD v1.4 sections 23.1, 28.5, 29;
contracts.md Today + Today Interview inputs; decision-log.md D-018/D-021/D-024;
Today policy/models/service, InterviewRepository, existing Interview service tests.
The user's v1.4 continuation authorization supersedes the old AGENTS P0F phase restriction.

## Owned paths
- backend/career_harness/core/today/ (narrow typed-input/policy/export changes only)
- backend/career_harness/services/today_service.py
- tests/unit/test_today_policy.py
- tests/integration/test_today_service.py
- tests/integration/test_today_api.py

All other files read-only. No migration, new API, frontend change or runtime writes.
Do not change shared semantics. Return CONTRACT CHANGE REQUEST if needed.

## Requirements
- Preserve existing item IDs/kinds, application-stage selection and priority ordering.
- For INTERVIEW-stage Applications only, use typed latest Interview reads and validate every
  pinned Application revision exactly; missing/mismatched provenance fails loud.
- Earliest SCHEDULED latest revision wins by UTC time then ID; terminal latest revisions never
  resurrect old schedules. Past scheduled records stay visible until an explicit status command.
- Item refs include selected exact Interview and its pinned Application; queue refs include every
  consulted Interview and historical Application revision, including excluded terminal records.
- Keep pure selection deterministic. Reject cross-Application and duplicate/conflicting refs.
- Runtime must never manufacture provenance for an unbacked timestamp. Existing direct policy
  callers should remain compatible where that does not weaken canonical runtime validation.
- No side effects, status changes, AI inference, external requests or new truth.

## Testing / Done
Use root repository .venv Python/Ruff. Run Today unit/service/API tests and Interview service
regression, Ruff on changed Python, format --check on changed Python, and git diff --check.
Test schedule ordering/ties, reordering invariance, no schedule, past schedule, latest cancelled/
completed suppression, exact historical Application pins, wrong/dangling refs and zero SQL writes.
API regression must expose the exact selected refs/time through authenticated GET /today.
Self-review, explicitly stage owned files and commit a focused feature on your branch. Never merge
or push. Return SHA, files, commands/results, residual limitations and any contract request.
