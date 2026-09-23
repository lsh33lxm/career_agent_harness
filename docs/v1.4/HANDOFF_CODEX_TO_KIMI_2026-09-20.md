# Agent Career Harness v1.4
# Codex -> Kimi Engineering Handoff

## A. Handoff Metadata

- Date: 2026-09-20 (Asia/Shanghai)
- From: Codex
- To: Kimi
- Repository: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness`
- Integration Worktree: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\integration`
- Integration Branch: `refactor/v1.4-integration`
- Verified Integration HEAD before handoff: `1fe3982` (`docs: record career read projections`)
- Main HEAD: `63ca32f` (`docs: add v1.4 product baseline`)
- Goal Status: ACTIVE. A completed milestone is not the complete PRD v1.4 stage.
- Handoff ID: `ACH-V14-CODEX-KIMI-2026-09-20`
- Handoff Status: materials verified; waiting for Kimi to verify and take ownership.

The active Goal includes the P0 vertical/capability/enhancement slices, the listed P1 capabilities,
the four long-term product loops and the PRD section 29 pluggability checks. Resume Core, Today UI
or Application/Outcome completion alone must not close the Goal.

## B. Current Git State

Before this handoff edit, `git status --short --branch` returned only
`## refactor/v1.4-integration`; `git diff`, `git diff --cached` and `git diff --check` were empty and
successful. The integration worktree was clean at `1fe3982`. This handoff and narrow status updates
are committed separately after that baseline.

`git branch --no-merged refactor/v1.4-integration` returned no branches. Every feature branch
below is reachable from integration. No feature worktree had staged, unstaged or untracked files.

| Worktree | Branch | HEAD | State |
| --- | --- | --- | --- |
| repository root | `main` | `63ca32f` | Intentionally unchanged |
| integration | `refactor/v1.4-integration` | `1fe3982` pre-handoff | Active |
| capability | `codex/v14-capability-core` | `5468c52` | MERGED |
| capability-read | `codex/v14-capability-read` | `3c2d18c` | MERGED |
| context | `codex/v14-context-core` | `c294937` | MERGED |
| enhancement-link | `kimi/v14-enhancement-link` | `2abdb2c` | MERGED |
| fact-promotion | `kimi/v14-fact-promotion` | `8a76ad2` | MERGED |
| job-requirement-core | `codex/v14-job-requirement-core` | `deadc25` | MERGED |
| match-persistence | `kimi/v14-match-persistence` | `4ff1ac3` | MERGED |
| match-resolver | `kimi/v14-match-resolver` | `38616c3` | MERGED |
| opportunity | `codex/v14-opportunity-core` | `e09c9a8` | MERGED |
| opportunity-ui | `codex/v14-opportunity-ui` | `c990589` | MERGED |
| project-evidence | `codex/v14-project-evidence-core` | `6df933e` | MERGED |
| project-read | `codex/v14-project-read-scanner` | `f3cfd9e` | MERGED |
| project-state-read | `codex/v14-project-state-read` | `3cb8d5f` | MERGED |
| resume-core | `kimi/v14-resume-core` | `c6bfe66` | MERGED |
| today-ui | `codex/v14-today-ui` | `7ebd4be` | MERGED |

The root `main` worktree is dirty only because it contains the intentionally untracked
`docs/Agent_Career_Harness_Codex_Goal_Pack/`. Do not delete, move, stage or commit it without
explicit user direction. Integration and every feature worktree were clean. There is no known
unmerged or WIP feature branch.

## C. Latest Verification Baseline

All entries were run during handoff unless marked otherwise.

| Surface | Result |
| --- | --- |
| Backend full | PASS: `334 passed, 3 skipped` in 162.86s |
| Backend skips | 3 expected Windows symlink privilege skips |
| Ruff lint | PASS; cache-write permission warnings only |
| Ruff format | FAIL BASELINE: 57 files would be reformatted, 97 already formatted; mostly line-ending churn; no files changed |
| Alembic | `0012_application_outcome (head)` |
| Migration focused | PASS: `49 passed` in 47.03s |
| Frontend tests | PASS: 3 files, 16 tests |
| Frontend typecheck/build | PASS: `tsc -b && vite build` |
| Frontend lint | NOT AVAILABLE: no lint script is defined |
| Browser responsive | NOT RE-RUN DURING HANDOFF; prior desktop and forced 390 px checks passed |
| Tauri/Rust | NOT RE-RUN DURING HANDOFF |
| Pre-edit `git diff --check` | PASS |

The successful backend commands used the existing repository-root `.venv`; default system Python
lacked pytest/Ruff. No dependencies were installed.

## D. Completed Product / Engineering Slices

| Slice | Status | Current capability |
| --- | --- | --- |
| Job | DONE | Immutable revisions, versioned requirements, exact Evidence/official Capability refs and atomic review commands |
| Capture | PARTIAL | Evidence/source/snapshot contracts exist; no production browser collector or complete capture UI |
| Opportunity | DONE | User-gated admission, additive persistence, exact reads, independent priorities and authenticated API/UI |
| Match / Gap | DONE | Frozen-input evidence-aware three-way policy with canonical Gaps |
| Match Persistence | DONE | Immutable assessments/results/gaps, additive 0009 and atomic write |
| Resolver / Replay | DONE | Exact reads and stored-manifest replay; drift/dangling provenance fail loud |
| Capability | PARTIAL | Graph, overlay, candidate rows, bindings/investment and typed reads exist; publishing/review UI and full planning do not |
| Project Evidence | PARTIAL | Scope-safe scanner, persistence and exact reads; no incremental scan or complete API/UI loop |
| Project Enhancement | PARTIAL | Gap-linked L1 task proposal/transition; no completion -> rescan -> Evidence orchestration |
| Career Fact / Promotion | DONE | Claim review and non-AI authority Fact promotion with exact Evidence refs |
| Resume Core | DONE | USER-owned base, reviewed patches, immutable revisions and exact qualified provenance |
| Today UI | PARTIAL | Responsive composition exists; displayed business data is static typed fallback |
| Application / Outcome | DONE at Core layer | Exact refs, user/receipt authority, immutable Outcomes and atomic services; no ATS execution |
| Read APIs | PARTIAL | Opportunity plus Resume/Application/Outcome GET projections; no Today/Project/Capability product API |
| Context Compiler | DONE for P0 basic | Five-asset selection and metadata-only Context Manifest persistence/read |
| Artifact/Audit/Backup | DONE | Content-addressed artifacts, events/idempotency, redaction and backup/restore |

`DONE` does not mean the whole user-visible loop or PRD stage is complete.

## E. Important Commits

| Commit | Meaning |
| --- | --- |
| `c6bfe66` / merge `df5f4d2` | Resume truth workflow and additive 0011 |
| `7ebd4be` / merge `989b47e` | Responsive Today workspace over typed fallback |
| `d61af6c` | Freeze Application/Outcome contract 0.7.0 |
| `5727af6` | Strengthen Application/Outcome exact-reference and authority invariants |
| `4b0bb68` | Application/Outcome persistence and services, additive 0012 |
| `83b7b91` | Authenticated Resume/Application/Outcome read APIs |
| `1fe3982` | Record career read projections in integration docs |
| `d43ebe4` | Claim review and Fact promotion, additive 0010 |
| `cadba69` | Link L1 enhancement tasks to canonical Gaps |
| `288ee30` | Exact Match resolver and replay |
| `b04d08e` | Durable Match/Gap persistence, additive 0009 |

There is no Today Read Model commit because that contract and implementation do not exist.

## F. Current Contracts

`docs/v1.4/contracts.md` is `v1.4-contract-0.7.0`, frozen for Wave 2 Application/Outcome.

| Area | State |
| --- | --- |
| Evidence / Fact authority | IMPLEMENTED |
| Job / JobRequirement | IMPLEMENTED |
| Opportunity / Priority separation | IMPLEMENTED; dynamic Suggested Priority policy missing |
| Match / Gap / replay | IMPLEMENTED |
| Capability official/personal/market/investment | MODELS + PERSISTENCE + READS; workflows incomplete |
| Project Evidence / L1 Enhancement | CORE + PERSISTENCE + READS; feedback orchestration incomplete |
| Context Manifest | IMPLEMENTED |
| Resume Base/Patch/Revision | IMPLEMENTED |
| Application / Outcome | IMPLEMENTED through 0012 and read APIs |
| Today Read Model | NOT FROZEN / NOT IMPLEMENTED |

Do not define a competing model. Freeze Today queue semantics and exact input revisions first.

## G. Database / Migration State

- Latest head: `0012_application_outcome`.
- The chain is linear from `0001_foundation` through `0012_application_outcome`.
- `0010_fact_promotion`: immutable claim/fact identities, revisions and Evidence refs.
- `0011_resume_core`: Resume identity/base, patches and immutable ResumeRevision records.
- `0012_application_outcome`: Application identities/revisions and immutable Outcome/Evidence rows.
- Recent migrations are additive and have disposable downgrade/re-upgrade rehearsals.
- No pending migration exists for Today, dynamic priority, incremental scan or market trend.
- M4 compatibility and real legacy cutover remain gated; never run them on user data without approval.

## H. Frontend State

- Today and Opportunities are real routes in the AppShell.
- Opportunities uses authenticated Core APIs for list/detail/admission/UserPriority.
- Today calls `getTodayFallback()` in `apps/desktop/src/pages/today/data.ts`; only health is live.
- Today focus, opportunities, confirmations and weekly content are static typed fallback.
- Projects, Capabilities, Resume, History, Me/Context and Settings are `SectionPage` placeholders.
- Resume/Application/Outcome reads are not consumed by desktop pages.
- There is no Today model, queue endpoint or dynamic priority consumer.

Replacing Today fallback remains READY, but only after its Core contract is frozen.

## I. Current Product Vertical Slice

| Step | Status | Gap |
| --- | --- | --- |
| Job / Capture | PARTIAL | Job canonical; capture adapters/UI incomplete |
| Evidence | DONE | Immutable provenance persistence and reads |
| Opportunity | DONE | User-gated admission and APIs |
| Match / Gap | DONE | Policy, persistence, resolver and replay |
| Project Evidence | PARTIAL | Safe full scan; no incremental/rescan orchestration |
| Project Enhancement | PARTIAL | L1 task exists; feedback loop incomplete |
| Career Fact | DONE | Explicit review/promotion |
| Resume Patch | DONE | Provenance-qualified and USER-reviewed |
| ResumeRevision | DONE | Immutable and content-hashed |
| Application | DONE at Core layer | No ATS and no desktop workflow |
| Interview | NOT STARTED beyond skeleton/placeholder |
| Outcome | DONE at Core layer | Reads exist; desktop workflow absent |
| Career History | PARTIAL | Application/Outcome projection; broader timeline absent |
| Career Reasoning | NOT STARTED as a complete service |
| Today / Next Action | PARTIAL | Static UI; no canonical queue/compiler |

There is no single end-to-end acceptance test proving the full P0 path with one coherent fixture.
Component slices are green, but the product vertical loop is not stage-accepted.

## J. Current Capability Slice

| Area | Status |
| --- | --- |
| Official Capability Graph | PARTIAL: versioned persistence/reads; publishing flow incomplete |
| Personal Overlay | PARTIAL: revisioned persistence/reads; user workflow/UI absent |
| Market Binding | PARTIAL: target/broad separation; no Broad Market Trend aggregation |
| Capability Gap | DONE through canonical Match Gap |
| Investment | PARTIAL: explainable model/storage; dynamic derivation incomplete |
| Capability Inbox | PARTIAL: candidate/status storage/reads; review service/UI absent |
| Visualization | NOT STARTED |

## K. Current Next READY Tasks

### NEXT READY #1 - Freeze Core-owned Today Read Model

Define item kinds, exact source revisions, deterministic ordering, explanations,
deadline/interview/application inputs and the invariant that SuggestedPriority recomputation never
changes UserPriority. Repository inspection confirms there is no existing contract/service/API.

### NEXT READY #2 - Prove the P0 vertical slice end to end

Add one coherent integration fixture covering canonical Job/Evidence -> Opportunity -> Match/Gap
-> Project Evidence -> reviewed Resume -> Application -> Outcome reads.

### NEXT READY #3 - Implement queue/recompute, then replace fallback

After contract freeze, implement Core queue compilation, dynamic SuggestedPriority, authenticated
read API and frontend adapter. Never put ranking logic in React or infer user intent from urgency.

Capability Inbox review, incremental Project Scan, Broad Market Trend, Capability Graph
visualization and CLI Adapter remain later P1 work.

## L. Recommended Next Workstream

**NEXT WORKSTREAM: Core-owned Today Read Model + Suggested Priority recomputation**

- Goal: deterministic, explainable Core next-action projection, then replace static business data.
- Why now: Today is the visible integration point and its typed UI boundary is waiting for Core.
- Dependencies: contract 0.7.0, exact career reads and independent priority persistence.
- Suggested branch/worktree: `kimi/v14-today-read-core`, created only after HEAD/ownership checks.
- Owned paths: new `backend/career_harness/core/today/**`, focused service/API/tests, then
  `apps/desktop/src/pages/today/**` and API client after backend review.
- Read-only initially: existing repositories/models, migrations and `TodayPage.tsx`.
- Forbidden: legacy writes, ATS/Feishu, credentials, unapproved main merge/push, destructive
  migrations and unrelated Core rewrites.
- Expected contract: exact refs, stable item IDs, typed reasons, deterministic sort, explicit
  stale/missing behavior, priority separation and no hidden mutations.
- Tests: ordering/reasons, dangling refs, UserPriority preservation, API auth/empty cases,
  frontend adapter tests, full pytest/Ruff/Vitest/build/diff check.
- Done: frozen contract, reviewed policy/read API, no React-owned ranking, fallback replaced with
  offline handling, relevant checks green and docs updated.

Also add the P0 end-to-end fixture before declaring broader stage completion.

## M. Open P2 / P3 / Follow-ups

No unresolved recorded P2 blocks integration. Remaining P3/non-blocking follow-ups are:

- Match duplicate-manifest refs converge to last entry and error typing is inconsistent.
- Malformed priority rows surface raw validation errors while Opportunity state is wrapped.
- Match manifest has a 64 KB fail-loud bound that may need real-data calibration.
- A future Opportunity Job re-link must revisit exact revision read assumptions.
- Capability exact point-read is absent; current released-version scan is correct but less efficient.
- Fresh Match callers must enumerate relevant Project Capability State refs.
- Replay callers must catch both resolution and drift error types.
- Claim review supports `SUPERSEDED` beyond current two-state contract wording.
- `ClaimRecord.reviewed_at` is write-only in staged revisions.
- Fact reads lack an independent revision-chain continuity defense.
- ProjectSourceManifest does not pin an exact Project revision; review before schema expansion.
- Completed enhancement tasks do not orchestrate rescan/new Evidence/promotion.

Do not reopen older findings already recorded as fixed.

## N. Known Risks

- Today fallback can drift from canonical data and create false product confidence.
- Frontend ranking would duplicate business truth and break replayability.
- Latest-at-read substitution would invalidate historical explanations.
- Broad format normalization would create noisy diffs; 57-file format failure is known.
- New schema must follow linear 0012 and remain additive/rehearsed.
- Provenance shortcuts can collapse Evidence into Fact or project presence into mastery.
- Retained worktrees create collision risk; verify ownership before edits.
- Root main has an untracked Goal Pack; never clean it incidentally.

## O. Product Invariants

- Local-first; Career Core owns canonical truth.
- Evidence != Fact != Signal != Decision != Outcome.
- ExtractedClaim/model/parser output requires promotion; AI cannot self-promote.
- SuggestedPriority != UserPriority; recomputation never changes UserPriority.
- Match != Priority.
- Official Capability Graph != Personal Capability Overlay.
- Project presence != Personal mastery.
- Coding Agent output != Resume Fact.
- Historical replay uses exact frozen refs; dangling/drifting provenance fails loud.
- Core is stable; execution providers are pluggable and never own truth.
- Workflow State != Business State.
- Opportunity != Application; Prepared != Submitted.
- User controls identity, legal/work authorization and final submission answers.

## P. Safety Boundaries

Continue to prohibit:

- production ATS submission or automatic final submission;
- production Feishu writes;
- destructive migration, legacy cutover or canonical import without approval;
- merge to or push of `main` without approval;
- automatic Career Fact overwrite or self-review;
- automatic UserPriority changes;
- credential, cookie, browser profile or raw legal/form answer persistence;
- any write-producing work in read-only legacy `agent_rader`;
- P2 L3 executor, product multi-agent runtime or plugin marketplace as incidental scope.

## Q. Exact Continuation Instructions For Kimi

1. Enter the integration worktree, not main, then run:

   ```powershell
   Set-Location 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\integration'
   git status --short --branch
   git log --oneline --decorate -10
   git worktree list
   git branch --all --verbose
   git diff
   git diff --cached
   git diff --check
   ```

2. Confirm branch `refactor/v1.4-integration` and a handoff docs commit whose parent is `1fe3982`.
   Stop if HEAD differs unexpectedly or integration is dirty.
3. Read this handoff, `STATUS.md`, PRD sections 2, 7, 8, 28, 29 and 32, then
   `contracts.md`, `progress.md`, `refactor-plan.md`, `integration-log.md`, `decision-log.md` and
   `migration-plan.md`.
4. Re-run the fastest baseline with the existing root `.venv`; do not install packages merely
   because system Python lacks pytest.
5. Start NEXT READY #1 as docs/contract-first Today Read Model work. Do not change schema or
   frontend business behavior before exact inputs, ordering and mutation boundaries are reviewed.
6. Create `kimi/v14-today-read-core` and a worktree only after clean read-only verification and
   path ownership confirmation. Do not restart from main or Wave 0.
7. Pause and ask Minnn for shared product-semantic changes, destructive migration, legacy cutover,
   production integration, main merge/push, ATS/Feishu, credentials or out-of-PRD scope.

Suggested Kimi opening prompt:

```text
Use project-handoff recovery. Work in the integration worktree and read
docs/v1.4/HANDOFF_CODEX_TO_KIMI_2026-09-20.md first. Verify Git/worktrees and the baseline before
editing. Continue the active PRD v1.4 Goal from NEXT READY #1; do not restart from main or Wave 0,
do not treat Today fallback as Core truth, and stop at every recorded approval boundary.
```
