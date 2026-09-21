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
