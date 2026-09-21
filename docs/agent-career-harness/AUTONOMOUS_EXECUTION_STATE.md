# v2.0 Autonomous Execution State

更新时间：2026-09-22

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
| B Career Knowledge | DONE (completion audit passed) | deterministic hybrid search + flagged-content quarantine |
| C Resume Studio | DONE (completion audit passed) | sandbox renderer、draft proposal/review、immutable render review 与 provenance |
| D Opportunity Radar | DONE (completion audit passed) | explainable multi-dimensional ranking + per-source retry/rate/disable policy |
| E Lifecycle / Replacement | DONE (completion audit passed) | shadow metrics、license/dependency scan、preview-gated switch 与 rollback recommendation |

## Final audit

- 状态：DONE — Slice A–E 均已完成 local/offline Definition of Done；当前没有阻塞本地继续工作的 P0/P1。
- Backend：`650 passed, 5 skipped`；跳过项均是 Windows symlink 创建权限/能力限制。
- Frontend：`18 test files, 59 passed`；Vite production build passed。
- Quality：Ruff `backend tests migrations` passed；`git diff --check` passed。
- Recovery：migration upgrade/downgrade、backup/restore、plugin lifecycle rehearsal 均通过；Legacy Agent Radar 仍只读。
- External boundary：真实 marketplace 下载、第三方 crawler/portal、Typst compiler、Feishu/Gmail/Notion/ATS 写入仍按 blocker ledger 保持隔离或 proposal-only。
- 当前入口：A–E 已收口；后续工作只从已登记 external boundary 获得授权后继续，或由新的产品授权开启下一切片。

## Desktop productization checkpoint (2026-09-22)

- 状态：Windows NSIS desktop lifecycle and clean-install acceptance passed。
- Tauri 2 启动打包的 Python sidecar，使用随机 loopback 端口与仅存在于内存/子进程环境的临时 token；前端配置通过 initialization script 注入。
- PyInstaller bundle 内含 Alembic 配置和 migration resources；全新 Data Root 自动升级到 `0025`。
- 首次安装等待窗口按 one-file 解包/安全扫描延长到 90 秒；sidecar stdout/stderr 保存到 Data Root `logs/desktop-sidecar.log`，不记录 token。
- 关闭桌面窗口会回收 PyInstaller bootloader 与 Python 子进程；重复验收确认监听端口释放。
- 干净安装数据库 Legacy 导入首轮 `7,575 new / 684 duplicate / 0 failed`，第二轮 `0 new / 7,575 unchanged`，源签名前后一致；未修改 Legacy。
- 构建：PyInstaller sidecar、Cargo check、Vite production、Tauri debug no-bundle、release NSIS 全部通过。
- 回归：backend `657 passed, 5 skipped`；frontend `19 files / 53 passed`；Ruff、Cargo check、Vite build 与 diff check 通过。

## Final requirement hardening

- Plugin Manifest v1 现在有 repository-owned 示例；插件详情页展示 source/commit、权限、license review、NOTICE、依赖扫描、审计、更新策略与卸载影响。
- 非 `builtin://` release 即使声明已知 SPDX license，也会因人工 license/NOTICE 与 install-script/vulnerability scan 未完成而保持 quarantined；不会被离线声明自动信任。
- Plugin knowledge search 默认脱敏 email、phone 与 credential-shaped text，并可限定 knowledge category；WeKnora blocked adapter 覆盖声明的 `search/read/ask/list` 能力。
- Migration `0022_job_source_terms_provenance` 将每次 source run 的 terms/robots/ToS note 与检查时间作为 immutable provenance 保存，并通过 upgrade/downgrade 验证。
- Focused：backend `32 passed`，Plugins UI `1 passed`；full：backend `650 passed, 5 skipped`，frontend `18 files / 59 passed`；Vite build、Ruff、diff check 通过。
- Independent review：APPROVE；历史 scan report、rollback、enable、healthcheck 与 invoke 的 quarantine bypass 已回归验证，P0/P1/P2/P3 均无未解决项。

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

- 状态：DONE — local/offline Resume Studio completion audit passed
- Migration：`0018_resume_studio_completion`，历史 unknown provenance 使用 NULL；Typst template downgrade 可逆并保留数据
- Renderer：HTML builtin；Typst 仅经 PluginRunner/PermissionGate/PluginEnvelope 注入 sandbox，当前机器无 sandbox 因此 disabled
- Flow：approved ResumeRevision → local draft → EvidenceRef-backed patch proposal → user review → immutable ResumeRevision → render Artifact → immutable user render review
- Verification：focused backend 8 passed；backend full 634 passed, 5 skipped；frontend 58 passed；Vite build、Ruff、diff check 通过
- Review：P1 findings fixed; no unresolved P0/P1. Real Typst compiler remains unavailable locally and is represented as disabled, not synthetic success.
- Next：Slice D completion audit

## Slice D completion checkpoint

- 状态：DONE — local/offline Opportunity Radar completion audit passed
- Migration：`0019_opportunity_radar_ranking_policy`，staging score breakdown 与 source policy additive/reversible；保留既有 staging CHECK constraints
- Ranking：deal-breaker、capability match、evidence coverage、interest/user-priority separation、location、salary、deadline、freshness 分项持久化；缺少个人证据明确为 0，不升级为 Fact
- Source policy：每来源独立 rate limit、retry budget、failure threshold、disabled state 与 last error；失败不创建 staging，连续失败后 fail-loud disabled
- Verification：focused Opportunity/API/migration 8 passed；migration/backend regression subset 56 passed；frontend 58 passed；Vite build、Ruff、diff check 通过
- External actions：JobSpy/WebMagic/portal crawler remains quarantined until license/ToS/network authority; manual/offline sources are the only active adapters
- Next：Slice E completion audit

## Recovery entry (historical)

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

## Completion audit correction (resolved)

- 2026-09-21：逐条对照长期执行提示词后，确认先前 A-E `DONE` 结论使用了弱于文档要求的验收证据。
- 已确认缺口：Slice B 只有 lexical search；Slice C 尚未证明第二隔离 renderer、自动保存与 drafter-reviewer；Slice D 尚未完整覆盖 deadline/location/salary/evidence ranking 和 per-source policy；Slice E 尚未完整覆盖 latency/provenance/error comparison、license/dependency scan 与 automatic rollback recommendation。
- 处理：保留所有已通过实现与提交，按原顺序补齐 B–E 审计缺口；B–E completion audit 已全部通过，最终状态见上方 Final audit。

## Slice B completion audit

- 状态：DONE — completion audit passed
- 补齐：deterministic local character n-gram vector cosine + lexical hybrid score；API/result 显式返回 lexical/semantic 分量和 search mode。
- 安全：prompt-injection flagged revision 默认不进入搜索或 plugin result；只有显式本地审核请求可包含。
- Verification：focused knowledge/API/contract `11 passed`；backend full `630 passed, 5 skipped`；frontend `58 passed`；Ruff、build、diff check 通过。
- Next：Slice C completion audit（已在后续 checkpoint 完成）。
## Model provider configuration checkpoint — 2026-09-21

- 状态：IMPLEMENTED / real provider connection pending user-supplied credentials.
- Providers：OpenAI、Anthropic、DeepSeek、OpenAI-compatible；配置服务地址、默认模型、超时与 API key。
- Secret boundary：API key 仅存 Windows Credential Manager；SQLite 只保存 `has_secret`，API/UI 只返回布尔状态与遮罩值。
- Connection gate：保存配置后状态为 `not_tested`；只有用户勾选外部请求确认且真实 `/models` 请求成功才成为 `connected`。测试不发送简历、岗位或项目内容。
- Migration：additive/reversible `0024_model_provider_configs`，保存非敏感配置与不可变连接审计行。
- Verification：backend full 654 passed / 5 Windows symlink skips；migration/API subset 50 passed；frontend 19 files / 52 passed and build；Windows Credential Manager synthetic write/read/delete passed；Ruff/diff passed.
- Next：bounded read-only GitHub repository analysis and project archive UI; real conversation remains blocked until credentials are explicitly configured.
## GitHub project analysis checkpoint — 2026-09-21

- 状态：IMPLEMENTED / real public-repository fetch blocked by current network.
- Flow：explicit URL + read-only network confirmation → bounded shallow clone with hooks disabled → static analysis → immutable `0025` profile → existing Project list/detail UI.
- Analysis：README、directory、dependency manifests、key modules、technology stack、tests、deployment、recent git activity、quantified outcome clues、risks and provenance.
- Safety：GitHub-only HTTPS URL；120s timeout；5,000 files / 100 MiB including `.git`；never execute repository code/install scripts；private token only in Windows Credential Manager and git environment, never argv/log/DB/API.
- Verification：backend full 656 passed / 5 Windows symlink skips；migration/API subset 52 passed；frontend 19 files / 53 passed and build；`0024→0025→0024→0025` and Ruff/diff passed；synthetic public/private flows passed.
- External acceptance：`https://github.com/octocat/Hello-World` failed because `github.com:443` is unreachable from this environment. No archive/profile was persisted for the failed fetch.
- Next：model-backed project conversation with exact analysis/resume/job references can proceed locally with fake provider contracts; real conversation needs configured credentials and network.
