# Agent Career Harness v1.4
# Kimi -> Codex Engineering Handoff

## A. Handoff Metadata

- Date: 2026-09-20 (Asia/Shanghai)
- From: Kimi (Lead)
- To: Codex
- Repository: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness`
- Integration Worktree: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\integration`
- Integration Branch: `refactor/v1.4-integration`
- Verified Integration HEAD at handoff: `693619c` (`merge: integrate incremental project rescan`)
- Main HEAD: `63ca32f` (unchanged; do not merge or push without explicit approval)
- Handoff ID: `ACH-V14-KIMI-CODEX-2026-09-20`
- Prior handoff: `docs/v1.4/HANDOFF_CODEX_TO_KIMI_2026-09-20.md` (superseded by this file)

The Goal remains ACTIVE. A completed milestone is not the complete PRD v1.4 stage.

## B. Git State

Integration was clean at `f0cf91d` when this handoff was written (`git status --short --branch`
returned only the branch line). All feature branches are merged into integration; no stale WIP.

New worktrees/branches added during this Kimi session (all merged unless noted):

| Worktree | Branch | Status |
| --- | --- | --- |
| match-persistence | `kimi/v14-match-persistence` | MERGED (`b04d08e`) |
| match-resolver | `kimi/v14-match-resolver` | MERGED (`288ee30`) |
| enhancement-link | `kimi/v14-enhancement-link` | MERGED (`cadba69`) |
| fact-promotion | `kimi/v14-fact-promotion` | MERGED (`d43ebe4`) |
| p0-vertical-slice | `kimi/v14-p0-vertical-slice` | MERGED (`f132709`) |
| today-read-core | `kimi/v14-today-read-core` | MERGED (`1d86b65`) |
| today-ui-adapter | `kimi/v14-today-ui-adapter` | MERGED (`c986936`) |

Root `main` worktree holds the intentionally untracked `docs/Agent_Career_Harness_Codex_Goal_Pack/`;
never clean it incidentally.

## C. Verification Baseline

Verified during this session with the root `.venv`:

- Backend full: `355 passed, 3 skipped` (3 known Windows symlink privilege skips).
- Ruff lint: PASS. `git diff --check`: PASS.
- Repo-wide `ruff format --check` has a KNOWN pre-existing baseline failure (~40-57 files,
  line-ending churn); only check files you touched.
- Frontend (pre-handoff): Vitest 16 passed, `tsc -b && vite build` PASS (Codex-verified earlier).
- Alembic head: `0012_application_outcome`; chain 0001..0012 linear; recent migrations additive
  with disposable downgrade rehearsals.

Verification commands:

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'
& $python -m pytest -q
& $ruff check backend tests migrations
git diff --check
```

## D. What This Kimi Session Completed

Starting from handoff `ACH-V14-20260919-01` (four staged Match/Gap files awaiting final review):

1. Match/Gap pure policy final review (independent reviewer + fixes) -> `073d3d1`.
2. Contract `0.4.0` froze Match persistence/resolver/replay (D-013, D-014) -> `08f1548`.
3. Durable Match persistence, additive 0009 -> merge `b04d08e`.
4. Exact input resolver + assess + stored-manifest replay -> merge `288ee30`; Lead read-path gap
   capability check `e82d6cc`.
5. Contract `0.4.1`: enhancement task write path -> merge `cadba69` (canonical Gap linkage,
   whitelist transitions).
6. Contract `0.5.0`: claim review + Fact promotion (D-015) -> merge `d43ebe4` (additive 0010;
   initial promotion binds to the accepted claim).
7. Contract `0.6.0`: Resume write path (D-016). Resume core itself was completed by Codex
   (`c6bfe66`, merge `df5f4d2`) while Kimi was rate-limited.
8. Codex completed Application/Outcome (contract `0.7.0`, additive 0012, read APIs) before this
   handoff cycle; verified by Kimi at baseline `334 passed`.
9. Contract `0.8.0`: Today read model (D-018) -> `16baf32`; Core implementation merge `1d86b65`.
10. P0 vertical slice end-to-end proof -> merge `f132709`
    (`tests/integration/test_p0_vertical_slice.py`, 2 tests over one coherent fixture).

Note: `docs/v1.4/decision-log.md` D-017 is Application/Outcome (Codex); the Today projection
decision is D-018. An earlier Kimi commit briefly misnumbered it; fixed in `196a12f`.

## E. Contracts

`docs/v1.4/contracts.md` is `v1.4-contract-0.10.0`. Frozen sections include: Evidence/Fact
authority, claim review + Fact promotion, Job/Requirement, Opportunity/Priority, Match/Gap
persistence+resolver+replay, Capability graph/overlay, Capability inbox review (`0.9.0`), Project
evidence/enhancement, incremental project rescan (`0.10.0`), Context manifest, Resume write path,
Application/Outcome, and the Today read model.

Do not define competing representations. Missing fields require a CONTRACT CHANGE REQUEST.

## F. In Flight At Handoff

None. `kimi/v14-incremental-rescan` was implemented by the Lead after the assigned coder stalled;
it was reviewed (APPROVE WITH FIXES), fixed (staleness commands now pin the motivating manifest per
D-020) and merged as `693619c`, verified at `371 passed, 3 skipped`.

Completed earlier in this session: `kimi/v14-today-ui-adapter` merged as `c986936` (Vitest 22
passed, build passed), and `kimi/v14-capability-inbox-review` merged as `3db621d`.

## G. Recorded Follow-ups (non-blocking)

From independent reviews this session; all in `docs/v1.4/progress.md` "Recorded follow-ups":

- Match stage duplicate manifest refs converge to last entry; error typing inconsistent.
- `OpportunityRepository.get_revision` priority rows surface raw ValidationError.
- Match manifest 64 KB bound may need calibration.
- Opportunity JobRef immutability-after-admission is assumed by exact reads.
- `CapabilityRepository.get_node` point read absent (list-by-version is exact but scans).
- Fresh Match callers must enumerate Project Capability State refs.
- Replay callers catch both MatchResolutionError and MatchReplayError.
- Claim review accepts SUPERSEDED beyond the contract pair.
- `ClaimRecord.reviewed_at` is write-only.
- Fact reads lack revision-chain continuity defense.
- ProjectSourceManifest does not pin an exact Project revision.
- Completed enhancement tasks do not orchestrate rescan/new Evidence/promotion.
- Today: deadline/interview ordering dimension is dormant (no data source yet); pending-review
  reads use raw SELECTs that should become typed repository reads.

## H. Next READY Work

1. Implement the incremental project rescan per contract `0.10.0` + D-020 (reuses the anchored
   readers; freshness changes are explicit commands with typed events; accepted evidence content
   is never mutated).
2. Remaining P1 items per the previous handoff, in rough priority: Broad Market Trend aggregation,
   Interview workflow, Capability graph visualization, CLI executor adapters. Each needs its own
   contract freeze + scoped prompt first.
3. The four long-term feedback loops (PRD section 32) and section 29 pluggability checks remain
   open; Today read model closes only the "next action" projection, not Career Reasoning.

## I. Safety Boundaries (unchanged)

- No production ATS submission, production Feishu writes, destructive migration, legacy cutover or
  canonical import without explicit approval.
- No merge to or push of `main` without explicit approval. Integration target is always
  `refactor/v1.4-integration`.
- Never `git add .`; explicit stage only. Never discard user or staged changes.
- Never write to the read-only legacy directory `D:\0.小红书投稿\小红书稿\9.15 三期\agent_rader`.
- AI output never self-promotes; SuggestedPriority never overwrites UserPriority; Project presence
  is not personal mastery; coding-agent output never becomes Resume Fact directly; historical
  replay uses exact frozen refs and fails loud on dangling provenance.
