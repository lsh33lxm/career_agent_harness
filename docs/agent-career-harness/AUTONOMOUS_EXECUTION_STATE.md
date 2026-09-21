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
| A Plugin Foundation | DONE (local/offline) | Slice B entry: local knowledge schema → proposal-only provenance |
| B Career Knowledge | NOT STARTED | 等待 Slice A DoD |
| C Resume Studio | NOT STARTED | 等待 Slice B DoD |
| D Opportunity Radar | NOT STARTED | 等待 Slice C DoD |
| E Lifecycle / Replacement | NOT STARTED | 等待 Slice D DoD |

## Slice A checklist

- [ ] Manifest v1 schema、Python/TypeScript types、validator
- [ ] Registry、lifecycle、permission gate、runner、envelope
- [ ] Reversible plugin foundation migration
- [ ] `echo-fixture` worker and `career-kb-local` read-only adapter
- [ ] Plugin API and `/plugins` page
- [ ] Failure/timeout/cancellation/idempotency/provenance/rollback tests
- [ ] Full backend/frontend regression and backup/restore rehearsal

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

## Recovery entry

Start with `git status --short --branch`, inspect this file, then continue at the first unchecked Slice A item. Record every blocker in `BLOCKERS.md` and every architectural decision in `DECISIONS.md`.
