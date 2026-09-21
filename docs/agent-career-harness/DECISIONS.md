# v2.0 Autonomous Decisions

## D-2.0-001 — Plugin boundary is scoped and deny-by-default

- 状态：`ACCEPTED FOR IMPLEMENTATION`
- 日期：2026-09-21
- 决定：插件通过 `PluginContext` 取得受限 Core/Artifact client、logger、clock、secret handle 和 cancellation token；运行时不向插件暴露 SQLAlchemy `Engine`、`Connection` 或 Session。
- 原因：保持 Career Core canonical truth，避免插件绕过 authority/provenance 约束。
- 影响：builtin、worker、MCP 首期共用 envelope 和 permission gate；外部写入默认拒绝。

## D-2.0-002 — Installation state is additive and reversible

- 状态：`ACCEPTED FOR IMPLEMENTATION`
- 日期：2026-09-21
- 决定：插件包、release、installation、permission、run、update plan、audit 使用独立 additive migration；不改写 v1.5 领域表。
- 原因：支持 upgrade/downgrade、backup/restore 和禁用后 Core 独立启动。

## D-2.0-003 — External adapters remain proposal/read-only in Slice A

- 状态：`ACCEPTED FOR IMPLEMENTATION`
- 日期：2026-09-21
- 决定：`career-kb-local` 首期只读，`echo-fixture` 仅用于 deterministic contract acceptance；不连接真实 WeKnora、ATS、Feishu、Gmail 或 Notion。
- 原因：凭据、许可和外部写入需要单独授权。

## D-2.0-004 — Lifecycle actions use both audit and DomainEvent

- 状态：ACCEPTED
- 日期：2026-09-21
- 决定：安装、启用、停用、健康检查、切换和回滚分别写不可变 plugin_audit_events 与既有 domain_event；请求重复时 audit 使用幂等键，调用重复时按 request_id 返回原 envelope。
- 原因：插件状态变化必须可追踪、可重放，并与现有 Core event boundary 保持一致。

## D-2.0-005 — Worker fixture uses a closure-backed scoped read facade

- 状态：ACCEPTED
- 日期：2026-09-21
- 决定：插件上下文只暴露 ScopedCoreClient 协议和受限 read-model allowlist；底层 Engine 由闭包捕获，插件对象没有 engine 或 connection 属性。
- 原因：满足“插件不得取得裸 DB 连接”的安全边界，同时允许 evidence provenance fail-loud 校验。

## D-2.0-006 — Knowledge imports are artifact-backed and proposal-first

- 状态：ACCEPTED
- 日期：2026-09-21
- 决定：知识导入先把原始 bytes 写入现有 Artifact Store，并创建 Evidence provenance；`knowledge_revision`、chunk、link 和 evidence ref immutable。导入记录默认 `proposed`，只有用户审阅 proposal 后才产生 `approved` revision。
- 原因：知识页面、外部资料和 LLM 推断不能绕过 Career Core 的 authority 边界；原始证据必须可重放、可验证、可回滚。
- 影响：local KB 可以返回 exact citation；悬空 evidence ref 直接失败；WeKnora 只作为 read-only adapter。

## D-2.0-007 — Slice B search uses deterministic lexical indexing first

- 状态：ACCEPTED FOR IMPLEMENTATION
- 日期：2026-09-21
- 决定：首期 `career-kb-local` 使用可重建的 SQLite chunk 索引和确定性关键词评分；向量/图检索保留为后续 adapter，不引入运行时网络或不可复现模型依赖。
- 原因：保持 local-first、离线可验收和结果可重放，同时不改变知识的 canonical/provenance 语义。
- 影响：当前搜索能力是轻量 lexical baseline；WeKnora 的远程 hybrid search 仍需单独配置与授权。

## D-2.0-008 — Resume Studio extends the existing Resume Core

- 状态：ACCEPTED
- 日期：2026-09-21
- 决定：TargetProfile、模板、RenderRun 和 ATS report 通过 additive migration 关联既有 immutable ResumeBase/Patch/Revision；不新建平行 Resume truth。
- 原因：现有 Resume Core 已具备 exact patch provenance 与 USER review gate，Studio 应承担编辑、预览、渲染和检查投影。
- 影响：生成结果进入 Artifact Store；渲染不能创建 Resume Fact，申请提交仍由用户单独确认。

## D-2.0-009 — First PDF renderer is dependency-free and repository-owned

- 状态：ACCEPTED FOR IMPLEMENTATION
- 日期：2026-09-21
- 决定：首个 `resume-render-html` 使用项目自有暖纸 HTML/CSS 模板和确定性本地 PDF writer，支持可提取文字层与页数检查；非 Latin 字符完整保留在 HTML preview，PDF baseline 会替换字体不支持的 glyph。
- 原因：不复制 Magic Resume 受限资产，不增加运行时外部依赖或网络，同时提供可重放的离线验收基线。
- 影响：高级 CJK 字体嵌入和隔离 LaTeX/Typst worker 是后续增强，不阻塞当前 Core-backed workflow。

## D-2.0-010 — Job sources stage evidence before Core admission

- 状态：ACCEPTED
- 日期：2026-09-21
- 决定：manual/offline JobSource 的原始 bytes 先进入 Artifact/Evidence 与 `job_staging_record`；URL/content fingerprint、terms status、suggested score 和 gaps 都是可审计投影。只有 `actor=user` 的 admission 才能创建 Job/Opportunity。
- 原因：外部职位是不可信输入，来源频率、parser 或建议分数都不能提升为 Core truth 或 User Priority。
- 影响：Resume 集成只输出 `proposal_only` seed；真实 crawler/portal adapter 必须先完成独立 license、ToS、网络权限与 fixture 审批。

## D-2.0-011 — Plugin replacement is preview-gated and version-pinned

- 状态：ACCEPTED
- 日期：2026-09-21
- 决定：同一 plugin ID 可注册多个 immutable release；installation 始终 pin 到一个版本。候选先 staging，再执行 Core compatibility、license、capability、permission diff 与 deterministic shadow fixture；只有全部通过后，用户 switch 才能改变 active pin。
- 原因：更新和替换必须可恢复，候选代码不能因被发现或下载就接管运行路径。
- 影响：`patch_auto` 仅自动准备 preview；不自动 switch。rollback 恢复 previous pin 并默认停用，保留 run/audit/artifact 以便重放。

## D-2.0-012 — Local hybrid search is deterministic and flagged content is quarantined

- 状态：ACCEPTED
- 日期：2026-09-21
- 决定：`career-kb-local` 将 lexical frequency 与本地字符 n-gram cosine vector score 合并，返回可解释的两个分量；不依赖外部 embedding 服务。检测到 prompt injection 的 revision 默认从搜索和 plugin result 排除，仅允许显式本地审核查询。
- 原因：满足首期轻量 hybrid search，同时保持 local-first、可重放与恶意文档隔离。
- 影响：后续真实 embedding adapter 可替换 vector provider，但不得改变 evidence citation、authority 或默认 quarantine 语义。

## D-2.0-013 — Resume renderer sandbox and draft promotion boundary

- 状态：ACCEPTED
- 决定：Typst 只能通过注入 sandbox runner、PluginRunner、PermissionGate 和 PluginEnvelope 执行；compiler identity/hash 与 worker checks 必须进入 RenderRun provenance。前端 draft 只能本地保存，必须携带 EvidenceRef 经 user-reviewed ResumePatch 后生成 immutable ResumeRevision 才能渲染。
- 原因：避免宿主进程越权、不可重放 provenance，以及 preview/export 分叉。
