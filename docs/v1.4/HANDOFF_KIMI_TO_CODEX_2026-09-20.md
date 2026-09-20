# Agent Career Harness v1.4
# Kimi -> Codex Engineering Handoff

## A. Handoff Metadata

- Date: 2026-09-20 (Asia/Shanghai)
- From: Kimi (Lead)
- To: Codex
- Repository: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness`
- Integration Worktree: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\integration`
- Integration Branch: `refactor/v1.4-integration`
- Verified feature integration HEAD after recovery continuation: `3626994` (`merge: integrate reviewed offline L1 acceptance`)
- Main HEAD: `63ca32f` (unchanged; do not merge or push without explicit approval)
- Handoff ID: `ACH-V14-KIMI-CODEX-2026-09-20`
- Prior handoff: `docs/v1.4/HANDOFF_CODEX_TO_KIMI_2026-09-20.md` (superseded by this file)

The Goal remains ACTIVE. A completed milestone is not the complete PRD v1.4 stage.

## B. Git State

Recovery found integration clean at `62f1ce8` and feature worktree clean at `e076daf`. The
interrupted docs were already committed (`ef3485e`, `709c2dd`, `f2727cf`, `1dbba22`);
implementation `ae39eb6` and fix `e076daf` were already merged. No changes were discarded.
Capability Visualization is complete after recovery review/regression and documentation closeout.

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

- Backend full after L1 acceptance merge: `552 passed, 3 skipped` (3 known Windows symlink
  privilege skips).
- Ruff lint: PASS. `git diff --check`: PASS.
- Repo-wide `ruff format --check` has a KNOWN pre-existing baseline failure (~40-57 files,
  line-ending churn); only check files you touched.
- Frontend latest verification: Vitest 39 passed, `tsc -b && vite build` PASS.
- Chromium synthetic populated/no-overlay fixtures passed 320/390/1366 px page-overflow checks;
  these do not constitute real-data or Tauri verification.
- Alembic head: `0013_interview`; chain 0001..0013 linear; recent migrations additive
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

`docs/v1.4/contracts.md` is `v1.4-contract-0.16.0` (Inbox client, D-026); L2 preparation
`0.15.0` / D-025, Today Interview
`0.14.1` / D-024 and Capability Workspace
`0.13.0` / D-023 is complete. Frozen sections include: Evidence/Fact
authority, claim review + Fact promotion, Job/Requirement, Opportunity/Priority, Match/Gap
persistence+resolver+replay, Capability graph/overlay, Capability inbox review (`0.9.0`), Project
evidence/enhancement, incremental project rescan (`0.10.0`), Context manifest, Resume write path,
Application/Outcome, and the Today read model.

Do not define competing representations. Missing fields require a CONTRACT CHANGE REQUEST.

## F. Completed After Handoff

- Offline L1 acceptance: `aa08afa`, merge `3626994`; independent APPROVE, P0-P3 none;
  focused 12 passed, full 552 passed, 3 skipped; full Ruff/changed format/diff passed.
  No production code changed. Section 29 evidence matrix: pluggability-acceptance.md.

- Inbox client: `6a18116` + historical pin fix `26c27f2`, merge `6ba054d`; final independent
  APPROVE, P0-P3 none. Focused 29 passed; full 551 passed, 3 skipped; frontend 39 passed/build;
  Ruff/5-file format/diff passed. Chromium responsive and receipt-refresh fixtures passed; real
  localhost API + disposable DB E2E proved acceptance/new graph/history/original historical pin.
  No real data reviewed; test servers stopped. Today runtime wiring fix `c984efc` was separately
  reviewed APPROVE and is included in full regression.

- L2 preparation: `56ae9d8` + privacy fix `1fac397`, merge `9101085`; contract 0.15.0 / D-025.
  Final independent review APPROVE, P0-P3 none. Focused 95 passed; full 534 passed, 3 skipped;
  Ruff/5-file format/diff passed. Original P2 task-text root locator disclosure is fixed.
  No CLI execution/network/canonical writes; preview is not consent; runner is unimplemented.

- Capability Workspace Visualization: Implementation `ae39eb6` + consistency fix `e076daf`, merged as `62f1ce8`; contract `0.13.0`, D-023. Recovery independent review of `f2727cf..e076daf`: APPROVE, no P0/P1/P2/P3. Focused backend 13 passed; full backend 403 passed, 3 known Windows symlink skips; frontend 27 passed; production build, full Ruff, 11 changed Python format checks and diff checks passed.
  The recovery verified the existing merge and independently reviewed the final implementation;
  it did not assume that the old reviewer prompt itself proved approval.


- `kimi/v14-broad-market-trend` completed as `f7cb3c6` and merged into integration as `c6efb8b`.
  Contract `0.12.0` + D-022 remain unchanged: the deterministic derived read model aggregates
  BROAD MarketBindings on read, records exact binding/evidence refs and performs zero canonical
  writes. Independent review returned APPROVE with no P0/P1/P2. Full verification passed
  `391 passed, 3 skipped`; Ruff passed.

`kimi/v14-interview-core` completed: reviewed (APPROVE, no P0/P1/P2), merged as `8c44620`,
verified at `381 passed, 3 skipped` with migration rehearsal `0012→0013→0012→0013` passed.

Completed in this session: `kimi/v14-today-ui-adapter` merged as `c986936`; `kimi/v14-capability-inbox-review` merged as `3db621d`; `kimi/v14-incremental-rescan` merged as `693619c` (Lead-implemented after the assigned coder stalled; reviewed APPROVE WITH FIXES, fixed, verified at `371 passed, 3 skipped`).

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
- Today: Interview schedules are integrated; deadline data is absent. Pending-review
  reads use raw SELECTs that should become typed repository reads.
- Broad Market Trend P3: consider a repository list read, DB-level MarketBinding immutability if an
  update path appears, a Literal trend version and stronger write interception. None blocks the
  next workstream.

## H. Next READY Work

1. W2-TODAY-INTERVIEW is DONE: `0b0fa6b` + timezone fix `ae53689`, merge `dc85365`;
   contract `0.14.1` / D-024, final review APPROVE, full 440 passed, 3 skipped.
   W2-L2-PREP is DONE at `9101085`, full 534 passed, 3 skipped.
   W2-INBOX-CLIENT is DONE at `6ba054d`, full 551 passed, 3 skipped.
   Section 29.7 L1 acceptance is DONE at `3626994`; full 552 passed, 3 skipped.
   Next preparation candidates: dynamic SuggestedPriority policy and bounded L2 runner/results.
   Neither is implemented; other section 29 replacement items remain explicit gaps, not passes.
   L2 runner/result handling still needs its own contract; real inference additionally needs
   explicitly selected project content, provider/model and budget.
   Local Codex 0.155.1 / Claude 2.1.214 are installed and login checks succeeded; no inference run.
   Claude tools-disabled mode is available; Codex read-only does not prove no-shell/scope-read
   isolation. Do not use unsafe file reads to extract context from scanner hash manifests.
2. The four long-term feedback loops (PRD section 32) and section 29 pluggability checks remain
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
