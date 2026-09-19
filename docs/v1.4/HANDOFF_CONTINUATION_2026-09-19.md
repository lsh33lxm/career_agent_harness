# Agent Career Harness v1.4 Continuation Handoff

## Handoff Record

- Handoff ID: `ACH-V14-20260919-01`
- Updated: `2026-09-19 Asia/Shanghai`
- Source thread: `01a0b40b-6a37-7603-b8cf-99638c756e46`
- Goal status at handoff: `paused`
- Handoff status: `材料已核对；等待新对话接手`
- Receiver thread: not created; Minnn will open a new conversation manually.

## Objective

持续接管 Agent Career Harness，依据 PRD v1.4 做受控增量重构：保留现有可用内核，先稳定共享契约，再用独立 worktree 和 scoped subagent 分波实现、review、集成与验证，最终跑通：

```text
Job
-> Opportunity
-> Match / Gap
-> Capability
-> Project Evidence
-> Project Enhancement Task
-> Resume Patch
-> Application
-> Outcome
```

不要把当前阶段的局部完成重新定义为整个目标完成。

## Authoritative Locations

Repository root:

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

Current integration worktree, continue here:

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\integration
```

Current branch:

```text
refactor/v1.4-integration
```

Important sources:

```text
AGENTS.md
AGENT_CAREER_HARNESS_PRD_v1.2.md
docs/prd/HANDOFF_V1_4.md
docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md
docs/v1.4/architecture-map.md
docs/v1.4/contracts.md
docs/v1.4/refactor-plan.md
docs/v1.4/progress.md
docs/v1.4/decision-log.md
docs/v1.4/migration-plan.md
docs/v1.4/integration-log.md
STATUS.md
```

Fact priority remains:

```text
verified repository state
> latest PRD v1.4 product direction
> handoff documents
> older plans/chat
```

`AGENT_CAREER_HARNESS_PRD_v1.2.md` still governs repository hard constraints, approved ADRs and P0F/P0B boundaries. Read it and `STATUS.md` before changing architecture or implementation.

## Git State

Current HEAD:

```text
5f48bba docs: advance to match gap implementation
```

Recent verified commits:

```text
5f48bba docs: advance to match gap implementation
0ee6388 feat: add atomic job requirement commands
3b33525 feat: add canonical job requirement persistence
d7b92e5 feat: persist immutable evidence provenance
b0f7b72 docs: advance to job persistence prerequisite
08218e2 test: cover project revision identity guards
e1182ab merge: integrate project state typed reads
7728282 merge: integrate versioned job requirement core
```

`main` remains at `63ca32f`; do not merge or push without a separate explicit instruction.

### Staged But Not Committed

The following four new files are staged:

```text
backend/career_harness/core/match_gap/__init__.py
backend/career_harness/core/match_gap/models.py
backend/career_harness/core/match_gap/policy.py
tests/unit/test_match_policy.py
```

Staged diff size:

```text
4 files changed, 1017 insertions
```

Do not discard, unstage or overwrite these files. They implement the first pure Match/Gap policy slice but have not passed the required independent final code review, so do not commit them immediately on resume.

Apart from this handoff file itself, no other tracked or untracked changes were present when this
handoff was written.

## Completed And Committed

### Wave 0 and Wave 1 foundation

- Repository reconnaissance, architecture map, shared contracts, migration plan and test baseline.
- Separate worktrees and scoped engineering prompts.
- Capability, Opportunity, Project Evidence and Context Core contracts.
- Opportunity persistence, command path, priority separation, Local API and desktop projection.
- Capability official graph/personal overlay persistence and typed reads.
- Project Evidence persistence, exact scope reads and handle-anchored scanner.
- Context Manifest metadata-only persistence and atomic compilation service.
- Project Capability State and Enhancement Task typed reads.

### Evidence provenance

Commit `d7b92e5` added additive migration `0007` and canonical immutable:

```text
EvidenceArtifact
EvidenceSource
SourceSnapshot
EvidenceRef
```

It includes typed reads, composite snapshot/artifact integrity, immutable triggers, credential/session rejection and fail-loud malformed-data behavior. Independent review found no P0/P1/P2.

### Job and JobRequirement

Commits `3b33525` and `0ee6388` added additive migration `0008`, typed repositories and atomic commands for:

```text
JobRevision
JobRequirement proposal
JobRequirement user review
```

Typed rows, generic revision, DomainEvent and idempotency commit in one transaction. Exact EvidenceRef, exact JobRevision and accepted official CapabilityNode membership fail closed. Only a USER command can review a proposal.

The spoofable caller-supplied `proposed_by_kind` parameter was removed. Proposal provenance is derived conservatively from `command.actor`: exact `user` becomes USER; every other actor becomes AGENT. Reviewer P2 tests were added for fake rule/user proposal provenance and complete rollback.

Independent review found no P0/P1. Final verification at that point was:

```text
237 passed, 3 skipped
Ruff passed
format check passed
git diff --check passed
```

## Accepted Architecture Decisions

Preserve all decisions in `docs/v1.4/decision-log.md`. The newest relevant decision is D-012:

- A `JobRequirement` identity is stable at `(requirement_id, job_id)`.
- Every Requirement revision pins an exact immutable `JobRef`.
- Later revisions may correct the exact Job revision or official capability mapping.
- A Requirement identity may never move to another Job.

Do not reintroduce the rejected interpretation that Requirement identity must remain permanently bound to its first exact Job revision.

Match/Gap contract decisions already frozen in `docs/v1.4/contracts.md`:

- Every accepted Job Requirement is exactly one of `COVERED`, `QUICK_TO_STRENGTHEN`, `CLEAR_GAP`.
- No synthetic overall match percentage is required.
- `COVERED` requires exact Personal Capability dimensions plus qualified non-AI Evidence Bindings.
- Project/code presence never proves personal mastery; it can provide proximity only.
- `CLEAR_GAP` means no qualified support in the frozen Core inputs, not that the user objectively lacks the capability.
- Match output is a proposal and must not mutate Career Facts, Personal Capability State, priorities, ontology or accepted resume material.

## Current Staged Match/Gap Slice

The staged implementation introduces a pure, side-effect-free `core.match_gap` package:

- frozen typed input manifest;
- `COVERED`, `QUICK_TO_STRENGTHEN`, `CLEAR_GAP`;
- typed reason codes;
- deterministic canonical ordering;
- exact cross-checks across Opportunity JobRef, JobRevision, accepted Requirements, official graph nodes, personal states, bindings and evidence sources;
- conservative exclusion of `AI_INFERRED` evidence;
- Project Evidence only qualifies when accepted, current and authority-consistent;
- Project Capability State can produce proximity but never personal coverage;
- no schema, repository, command, event, priority, Fact or Resume write.

This slice deliberately does not claim durable persistence or cross-process replay.

### Current verification

Run on the staged version:

```text
tests/unit/test_match_policy.py: 10 passed
full backend suite: 247 passed, 3 skipped
full Ruff lint: passed
focused Ruff format check: passed
staged diff check: passed
```

The three skips are existing Windows symlink-creation permission limitations in the legacy importer/project scanner tests.

### Review status

One pre-implementation Evidence/audit design review completed and identified the persistence boundaries below. The requested final implementation code review did not complete because the reviewer hit:

```text
429 Too Many Requests
request id: fb334750-714c-4306-a613-5d544e85a7b2
```

This is a review infrastructure failure, not a test or code failure. Final code review is still required.

### Known review targets

Inspect these before committing:

1. Confirm every `COVERED` path requires both personal scope booleans and qualified evidence for every required scope.
2. Confirm unqualified/stale/AI evidence cannot accidentally create coverage.
3. Confirm Project Capability State basis is sufficiently validated for a pure typed input, or add exact basis-source validation before using it as proximity.
4. Confirm the frozen manifest contains enough exact provenance for the next persistence stage; generic EvidenceRef IDs are immutable, while Project Evidence uses ID + revision.
5. Confirm extra/unreferenced evidence inputs fail closed and missing/dangling EvidenceRefs cannot degrade silently into QUICK/CLEAR.
6. Confirm canonical input ordering makes equivalent reordered inputs produce identical business output.
7. Confirm `MatchAssessment` documentation does not imply durable identity, persisted replay or a resolvable Gap record.

## Known Persistence Gaps After The Pure Policy

These are real next-stage requirements, not reasons to discard the pure policy:

- There is no MatchAssessment/Gap schema or repository yet.
- `ProjectEnhancementTask.target_gap_id` is not yet backed by a resolvable canonical Gap record or FK.
- Durable immutable proposals, command/event/idempotency, historical query and cross-process replay require an additive migration, likely `0009` after design review.
- `OpportunityRepository.get()` currently reads only the current projection. Any resolver/persistence that depends on historical Opportunity fields must add an exact revision read. The pure policy currently uses Opportunity only as a frozen ID/revision + JobRef input.
- `capability_evidence_binding.evidence_ref_id` predates migration `0007` and has no DB FK. A Match input resolver must call `EvidenceRepository.get()` for every generic EvidenceRef and fail loud on dangling provenance.
- Historical replay must use persisted exact ordered Requirement refs. It must not rebuild history from `JobRepository.list_requirements_for_job()`, whose semantics are latest-first then Job-revision/status filtering.
- Current `InvestmentState` arithmetic is deterministic, but its floating factors are not yet pinned to evidence-derived inputs. Do not claim those factors are evidence-derived.

## Immediate Resume Procedure

The first resumed action is a read-only final review of the staged four-file Match/Gap slice. Do not start migration `0009` first.

```powershell
Set-Location 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\integration'
git status --short --branch
git diff --cached --check
git diff --cached -- backend/career_harness/core/match_gap tests/unit/test_match_policy.py
```

Then:

1. Run or delegate one independent final review against the known review targets.
2. Fix all real P0/P1 findings and justified P2 test gaps.
3. Run focused tests, full Ruff, format check and full pytest.
4. Review the staged diff again and explicitly stage only the four Match/Gap files.
5. Commit only after review passes. Suggested commit message:

```text
feat: add evidence-aware match gap policy
```

6. Update `STATUS.md`, `progress.md`, `refactor-plan.md`, `integration-log.md` and `decision-log.md` in a separate docs commit.
7. Design the next additive persistence/resolver slice. Freeze exact Opportunity/Job/Requirement/Graph/Personal State/Evidence/Project State refs before schema work.

## Verification Commands

Use the repository virtual environment:

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest tests/unit/test_match_policy.py -q
& $ruff check backend tests migrations
& $ruff format --check backend/career_harness/core/match_gap tests/unit/test_match_policy.py
& $python -m pytest -q
git diff --cached --check
```

## Safety And Scope Boundaries

- Always address the user as `Minnn`; default language Chinese.
- Do not push or merge `main`.
- Do not write to the read-only legacy directory:

```text
D:\0.小红书投稿\小红书稿\9.15 三期\agent_rader
```

- Never use `git add .`; stage explicit files only.
- Do not discard user changes or staged Match/Gap work.
- Do not fabricate JobRevision records to repair legacy Opportunity orphans.
- Preserve `Evidence != Fact != Signal != Decision != Outcome`.
- AI/model/parser output cannot self-promote to canonical Fact or accepted Requirement.
- SuggestedPriority must never overwrite UserPriority.
- Official Capability Graph and Personal Capability Overlay remain separate.
- Project presence is not personal mastery.
- Coding-agent output cannot directly become Resume Fact.
- No destructive migration, legacy cutover, real ATS submission, production Feishu write, P1/P2 expansion, plugin marketplace or product multi-agent runtime without the corresponding gate/approval.

## Worktree Inventory

Existing worktrees remain available and must not be recreated blindly:

```text
integration          refactor/v1.4-integration
capability           codex/v14-capability-core
capability-read      codex/v14-capability-read
context              codex/v14-context-core
job-requirement-core codex/v14-job-requirement-core
opportunity          codex/v14-opportunity-core
opportunity-ui       codex/v14-opportunity-ui
project-evidence     codex/v14-project-evidence-core
project-read         codex/v14-project-read-scanner
project-state-read   codex/v14-project-state-read
```

All listed feature work has already been integrated as recorded in `docs/v1.4/integration-log.md`; do not merge those branches again.

## New Conversation Opening Prompt

Use this in the new conversation:

```text
$project-handoff

Minnn 要继续 Agent Career Harness v1.4 重构。请先读取并核对：

D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\integration\docs\v1.4\HANDOFF_CONTINUATION_2026-09-19.md

Handoff ID: ACH-V14-20260919-01
Integration worktree: D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\integration
Branch: refactor/v1.4-integration

当前四个 Match/Gap 文件已 staged、测试通过，但独立 final review 因 429 未完成。先只读核对 Git 状态、staged diff、关键契约和 handoff 中的 known review targets；确认没有差异后，直接继续 final review、修复、全量验证和聚焦 commit。不要丢弃 staged changes，不要从 main 开始，不要重新合并已集成 worktree，不要写 agent_rader，不要 push 或 merge main。
```
