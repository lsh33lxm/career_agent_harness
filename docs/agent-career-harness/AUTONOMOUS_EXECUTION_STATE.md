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
| C Resume Studio | DONE (local/offline) | Migration `0016_resume_studio` |
| D Opportunity Radar | DONE (local/offline) | Migration `0017_opportunity_radar` |
| E Lifecycle / Replacement | DONE (local/offline) | versioned registry → shadow preview → switch/rollback |

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

## Slice C checkpoint

- 状态：DONE — local/offline Resume Studio vertical slice
- Migration：`0016_resume_studio`，TargetProfile/template/render/ATS records immutable and additive
- Flow：approved ResumeBase/Revision → user TargetProfile → evidence-constrained Patch proposal/review → immutable revision → HTML preview/PDF Artifact → ATS report
- Renderer：repository-owned `resume-render-html` template；未复制 Magic Resume 源码、模板、字体或资产
- Verification：focused backend/API/migration/restore 59 passed；backend full 622 passed, 5 skipped；frontend 57 passed；Vite build passed；Ruff/diff check passed
- External actions：ATS submit and third-party template execution remain blocked/proposal-only
- Next slice：Slice D — Opportunity Radar，manual/offline sources first

## Recovery entry

Start with `git status --short --branch`, inspect this file, then continue at the current Slice entry. Record every blocker in `BLOCKERS.md` and every architectural decision in `DECISIONS.md`.

## Slice D checkpoint

- 状态：DONE — local/offline Opportunity Radar vertical slice
- Flow：manual/offline source → Artifact/Evidence → staging → fingerprint dedupe → match/gap/rank → explicit user admission → Opportunity
- Resume handoff：仅对 user-admitted staging 生成 `proposal_only` seed，仍须经过 Resume Studio target/patch/review gate
- Verification：focused backend/API/migration `5 passed`；backend full `627 passed, 5 skipped`；frontend `58 passed`；Vite build、backup/restore、Ruff、diff check 通过
- Review：APPROVE；P0/P1 none。第三方 crawler/portal 接入因 license/ToS/credentials 保持 quarantined
- Next slice：Slice E — Plugin Lifecycle / Replacement

## Slice E checkpoint

- 状态：DONE — local/offline Plugin Lifecycle / Replacement
- Flow：release stage → compatibility/license/permission scan → deterministic shadow run → user switch → health observation/manual rollback
- Safety：candidate staging 不改变 active pin；unknown license、Core incompatibility、capability loss、permission escalation 或 shadow mismatch 会拒绝 switch；quarantined plugin 无法启用
- Policy：`notify`（默认）、`patch_auto`、`manual` 可记录；`patch_auto` 只自动准备检查，不自动执行任意代码或 switch
- Recovery：旧 release/handler 保留；rollback 恢复 previous pin 并停用；uninstall preview 不删除 Core truth、Artifact bytes、run 或 audit
- Verification：focused backend/API `9 passed`；backend full `629 passed, 5 skipped`；backup/restore/lifecycle rehearsal `9 passed`；frontend `58 passed`；Vite build、Ruff、diff check 通过
- Review：APPROVE；P0/P1 none。真实 marketplace 下载与 external-write adapters 仍需单独授权
- Next：A-E final audit；后续只处理已登记 external blockers 或新的产品授权
