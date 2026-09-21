# v2.0 Autonomous Execution State

更新时间：2026-09-21

## Authority

- 产品依据：`docs/prd/ACH_v2.0_PRD_插件化职业智能平台.md`
- 执行依据：`docs/prd/ACH_v2.0_Codex_长期自主执行提示词.md`
- 当前分支：`refactor/v1.4-integration`
- 起始基线：`084017c`
- Legacy Agent Radar：只读；本轮不修改原始文件

## Slice state

| Slice | 状态 | 当前入口 |
| --- | --- | --- |
| A Plugin Foundation | DONE (local/offline) | Slice A commit `e2f2807` |
| B Career Knowledge | DONE (local/offline) | Slice C entry: ResumeBase → proposal-only render chain |
| C Resume Studio | IN PROGRESS | 先冻结 Core-backed contract、fixture 和测试 |
| D Opportunity Radar | NOT STARTED | 等待 Slice C DoD |
| E Lifecycle / Replacement | NOT STARTED | 等待 Slice D DoD |

## Slice A checklist

- [x] Manifest v1 schema、Python/TypeScript types、validator
- [x] Registry、lifecycle、permission gate、runner、envelope
- [x] Reversible plugin foundation migration
- [x] `echo-fixture` worker and `career-kb-local` read-only adapter
- [x] Plugin API and `/plugins` page
- [x] Failure/timeout/cancellation/idempotency/provenance/rollback tests
- [x] Full backend/frontend regression and backup/restore rehearsal

## Safety boundaries

- Core/SQLite remains canonical for approved career records.
- Plugins receive scoped clients and never a raw SQLAlchemy engine or connection.
- Proposal, inference and external data remain non-canonical until user review.
- No external writes, credential acquisition, force push, destructive migration or Legacy mutation.

## Slice A checkpoint

- 状态：DONE — local/offline Slice A
- Backend：613 passed, 5 skipped
- Frontend：56 passed；npm run build passed
- Ruff：backend tests migrations passed
- Migration：0014_plugin_foundation，upgrade/downgrade and backup/restore passed
- Acceptance：echo worker install preview → install → enable → invoke → disable → rollback passed
- External actions：none；real Feishu/Gmail/Notion/ATS writes remain blocked by policy
- Next slice：Slice B — Career Knowledge / Wiki，starting with local knowledge schema and proposal-only provenance

## Slice B checkpoint

- 状态：DONE — local/offline Slice B
- Migration：`0015_knowledge_foundation`，upgrade/downgrade passed；backup/restore rehearsal passed
- Backend focused：6 passed；migration/backup focused：50 passed
- Backend full regression：619 passed, 5 skipped (Windows symlink permission limitations)
- Frontend：56 passed；`npm run build` passed
- Ruff：`backend tests migrations` passed；`git diff --check` passed
- Acceptance：document import → Artifact/Evidence provenance → local search/citation → proposal review → revision diff/rollback/index rebuild passed
- External adapter：`career-kb-weknora` is read-only and blocked until endpoint, credentials, license and terms are verified
- Next slice：Slice C — Resume Studio，starting with Core-backed Base/Target/Revision proposal chain

## Recovery entry

Start with `git status --short --branch`, inspect this file, then continue at the current Slice entry. Record every blocker in `BLOCKERS.md` and every architectural decision in `DECISIONS.md`.
