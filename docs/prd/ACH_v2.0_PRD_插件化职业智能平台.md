# Agent Career Harness v2.0
## 插件化职业智能平台 PRD（供 Codex 开发）

版本：v2.0-draft  
日期：2026-09-21  
基线：v1.5 状态文档、Career Core、SQLite migrations 0001–0013、现有本地优先与证据约束原则

---

## 1. 产品结论

Agent Career Harness 不应直接复制或拼接 WeKnora、Magic Resume、JobHunter、AI Job Search 的代码，而应把它们拆成可替换的能力提供方：

1. Career Core 仍是新批准职业记录的唯一 canonical truth。
2. 插件只能通过稳定协议读写 Core 命令、读模型和 Artifact Store，禁止直接写 SQLite。
3. LLM 只能产生检索结果、提案、草稿或评估；不能自动把推断升级为 Fact、Capability、Resume Fact 或 Outcome。
4. 所有外部采集、网络访问、凭据使用和外部写入都必须声明权限，并经过用户授权。
5. 插件可安装、停用、升级、替换、回滚，但每次变化都必须可审计、可重放、可恢复。

### 1.1 v2.0 目标

- 建立 Plugin SDK、Manifest、Registry、运行时和 Marketplace 面板。
- 建立 Career Knowledge/Wiki 能力：文档、个人经历、项目证据、面经、偏好和市场资料可检索、可引用、可版本化。
- 完成 Resume 工作流：编辑、目标岗位定制、预览、PDF、ATS 检查、差异和用户审核。
- 完成 Job Discovery 工作流：多来源采集、规范化、去重、匹配、排序和 admission staging。
- 把现有 Projects、Resume、Opportunities、History、Feishu、Executor 接入插件边界，而不是再造平行 truth。

### 1.2 明确不做

- v2.0 不做无人值守批量投递、不绕过登录/验证码/反爬或网站条款。
- 不做 Legacy canonical cutover；Legacy Agent Radar 仍只读、可回放、可恢复。
- 不把任意 GitHub 仓库直接当作可信插件；必须经过许可、来源、权限、依赖和安全检查。
- 不把外部项目数据库、CSV、Markdown 或向量库提升为 Career Core truth。

---

## 2. 参考项目的采用策略

| 项目 | 可借鉴能力 | 在本系统中的落点 | 风险与边界 |
|---|---|---|---|
| Tencent/WeKnora | 混合检索、RAG、ReAct、Wiki 自动生成、页面修订/回滚、知识图谱、MCP/CLI、任务队列和观测 | `career-kb-weknora` adapter；初期只读检索/问答/文档读取，Core 保存已批准事实和 provenance | WeKnora 可作为外部知识引擎，不能让其内部 KB 取代 Core；凭据、网络和知识库范围必须按插件权限隔离 |
| JOYCEQL/magic-resume | 实时预览、主题、响应式编辑、自动保存、本地存储、PDF 导出 | 独立实现 `resume-editor` 与 `resume-renderer` 合约；复用交互思想和验收标准 | 当前仓库 README/LICENSE 明确限制商业使用；未经许可不得复制其源码、模板或作为商业 SaaS 依赖 |
| webmagic-io/jobhunter | 抓取器、Pipeline、规范化后持久化的简单范式 | `job-source` adapter 示例或离线 fixture；把抓取结果先放 staging，再通过 admission 进入 Core | 仓库是较早的 Spring/WebMagic/MyBatis demo，不作为生产级抓取器；必须遵守 robots、站点条款、限速和来源声明 |
| MadsLorentzen/ai-job-search | `/setup`、`/scrape`、`/rank`、`/apply`、`/interview`、`/outcome`、drafter-reviewer、ATS/PDF 验证、可插拔 portal/template skills | 将其命令流转成 Core Task/Execution Run 和插件能力；优先实现 `rank`、`apply-draft`、`interview-prep` | 不把 Claude Code session 当职业身份；所有结果写入 proposal/revision，必须经过用户确认 |
| Gsync/jobsync（补充参考） | 自托管 tracker、简历审阅、岗位匹配、应用跟踪和分析 | 只参考信息架构和面板，不导入其数据库模型 | 先确认当前许可证、依赖和安全状况，再决定是否做 adapter |
| speedyapply/JobSpy（补充参考） | 多 job board 并发聚合、统一 dataframe、去重基础 | `jobspy-source` 可选 source adapter，默认低频、个人使用、可关闭 | 抓取稳定性、站点 ToS、字段缺失和封禁风险；禁止把代理绕过写成产品承诺 |

### 2.1 许可规则

每个插件安装前必须生成 `license_report`：SPDX 标识、仓库 URL、commit/tag、依赖许可证、商业限制、NOTICE 要求和人工复核状态。许可证不明确或含非商业限制的项目只能进入“外部参考/隔离运行”状态，不能打包到主产品发行物。

---

## 3. 总体架构

```text
Desktop / Web / Feishu projection
            |
      Plugin Marketplace UI
            |
Plugin Registry + Policy Gate + Lifecycle Manager
            |
Plugin Runtime (in-process adapter / worker / MCP / CLI sandbox)
            |
Stable Capability Contracts + Event/Outbox + Artifact refs
            |
Career Core + SQLite + Artifact Store + deterministic read models
```

### 3.1 运行时类型

- `builtin_adapter`：随产品发布、经过测试、可访问受限 Core service。
- `worker_plugin`：独立进程/容器，使用 JSON/NDJSON 协议，拥有最小文件和网络权限。
- `mcp_plugin`：通过 MCP 暴露只读或明确声明的命令。
- `cli_skill`：外部 CLI/skill，必须提供 `--format json`、版本、退出码和离线测试。
- `projection_plugin`：只生成 UI/导出投影，不拥有 canonical data。

v2.0 首期只实现 `builtin_adapter`、`worker_plugin`、`mcp_plugin` 三类；任意前端代码注入、任意宿主进程执行和自动安装第三方依赖延期。

### 3.2 Plugin Manifest（必须版本化）

```json
{
  "id": "career-kb-weknora",
  "name": "Career Knowledge / WeKnora",
  "version": "0.1.0",
  "api_version": "1",
  "type": "mcp_plugin",
  "source": {
    "repo": "https://github.com/Tencent/WeKnora",
    "ref": "v0.8.0",
    "commit": "immutable-sha",
    "license": "Apache-2.0"
  },
  "capabilities": ["knowledge.search", "knowledge.read", "knowledge.ask"],
  "permissions": {
    "network": ["configured-weknora-host"],
    "filesystem": ["artifact-store:read"],
    "secrets": ["weknora-api-key"],
    "external_write": false
  },
  "data_contracts": ["EvidenceRef", "KnowledgePassage", "PluginEnvelope"],
  "healthcheck": {"command": "health", "timeout_ms": 5000},
  "replacement": {"compatible_capabilities": ["knowledge.search", "knowledge.read"]}
}
```

Manifest 还必须包含依赖、最低/最高 Core 版本、配置 schema、数据迁移版本、成本/超时上限、用户可见说明和安全/条款链接。

### 3.3 通用结果信封

```json
{
  "request_id": "uuid",
  "plugin_id": "...",
  "plugin_version": "...",
  "capability": "job.search",
  "status": "ok|proposal|blocked|error",
  "data": {},
  "evidence_refs": [],
  "warnings": [],
  "error": null,
  "started_at": "ISO-8601",
  "finished_at": "ISO-8601"
}
```

插件输出不能绕过该信封；任何 `proposal` 必须有审阅入口，任何 `blocked` 必须告诉用户缺少的授权或权限。

---

## 4. 核心产品模块

### 4.1 Plugin Marketplace

新增 `/plugins` 页面，分为：已安装、可发现、更新、审计、权限。

每张插件卡片展示：名称、能力、版本、来源仓库、固定 commit/tag、许可证、权限、风险级别、兼容性、最近健康检查、最近运行、数据范围、更新策略和回滚点。

用户操作：

- 查看 manifest、源码链接、license report、权限 diff、依赖和审计日志。
- 安装（先扫描/预览，再确认）、启用、停用、健康检查、更新、替换、回滚、卸载。
- 设置更新策略：仅提醒、补丁自动更新、手动批准；默认“仅提醒”。
- 设置插件级模型、网络域名、数据范围、成本上限和外部写入策略。

替换流程：snapshot → install candidate → contract tests → fixture shadow run → compare output/provenance → user approve → switch pointer → observe → rollback if degraded。

### 4.2 Career Knowledge / Wiki

知识域：个人事实、项目证据、技能、面经、STAR 案例、偏好、目标岗位、公司资料、市场信号、模板和历史申请。

每条知识必须有：`knowledge_id`、正文/结构化字段、来源、`evidence_refs`、authority、confidence、valid_time、created_by（USER/LLM/PLUGIN）、revision、标签和状态（draft/proposed/approved/archived）。

功能：

- Markdown/PDF/DOCX/网页/项目扫描结果导入；保留原始 Artifact 和 hash。
- 混合检索（关键词 + 向量；图检索可选），结果返回原文片段和 exact provenance。
- LLM 生成 Wiki 页面、关系和摘要时只生成 proposal；用户可接受、编辑、驳回、回滚。
- Wiki 页面、chunk、引用关系均有 revision/diff/rollback。
- 提问结果必须区分“个人事实”“推断”“市场资料”，不允许把外部资料当个人经历。

首个 adapter：`career-kb-local`（本地 Markdown/SQLite/轻量索引）；第二个 adapter：`career-kb-weknora`（远程或本地 WeKnora）。

### 4.3 Resume Studio

数据链：`ResumeBase → TargetProfile → PatchProposal → ResumeRevision → RenderRun → OutputArtifact → Application`。

功能：

- Base/Revision/目标岗位并排查看；字段级 diff 和 claim provenance。
- 实时预览、主题、响应式编辑、自动保存和 PDF 导出。
- 模板 registry：HTML/CSS、LaTeX、Typst 等由插件提供；模板必须有 compile command、字体、页数限制和 test fixture。
- 目标岗位定制：提取 requirements，映射 Evidence/Capability，生成可审核 patch；不支持的关键词必须显示为 gap，禁止 keyword stuffing。
- drafter-reviewer：生成者与审阅者分离；最终生成前执行页面布局、文字层、联系方式、阅读顺序和 ATS 关键词检查。
- 每次导出形成不可变 Artifact，记录模型、模板、插件版本、输入 revision、检查结果和用户批准。

首期目标：先做独立的 Core-backed editor/preview/render；Magic Resume 只作为功能与验收参考，不直接复制源码。

### 4.4 Opportunity Radar

`job-source` 统一接口：`search(query)`, `fetch_detail(ref)`, `normalize(raw)`, `health()`, `terms()`。

来源优先级：手动 URL/文本、RSS/API、`ai-job-search` portal skill、WebMagic/JobHunter pattern、JobSpy adapter；每个来源独立限速、robots/ToS 记录、失败重试和禁用开关。

规范化字段：标题、公司、地点、远程、薪资、发布日期、截止日期、要求、来源 URL、抓取时间、原文 hash、source plugin、terms status。

流程：collect → staging → dedupe → match/gap → rank → user admission → Opportunity revision。JobSource 不得直接创建 approved Job/Opportunity。

排序维度：硬性 deal-breaker、能力匹配、证据覆盖、兴趣/优先级、地点/薪资、截止日期、来源新鲜度。Suggested Priority 与 User Priority 仍分离。

### 4.5 Application / Interview / Outcome

实现 `setup → scrape → rank → apply-draft → review → render → user-submit → interview-prep → outcome` 的 Task 链。

外部提交默认只生成 `submission_plan`，不自动发送。Gmail/Notion/Feishu 只能通过显式 adapter 和审批队列提出变更；冲突、无法匹配和 offer 状态不得猜测。

---

## 5. Core 数据模型与迁移建议

新增 migrations 0014+：

- `plugin_packages`：manifest、source、license、trust、content_hash。
- `plugin_releases`：版本、commit、依赖、兼容性、scan report。
- `plugin_installations`：状态、配置、enabled、pinned release、last health。
- `plugin_permissions`：网络、文件、secret、external_write、scope。
- `plugin_runs`：request、input hash、output hash、status、cost、evidence refs、trace。
- `plugin_update_plans`：候选版本、测试结果、迁移、approval、rollback snapshot。
- `knowledge_entries` / `knowledge_revisions` / `knowledge_links`：只保存 approved/proposed metadata 与 provenance；原始 bytes 进入 Artifact Store。
- `render_runs` / `template_registrations` / `ats_reports`：与 ResumeRevision 关联。
- `job_source_runs` / `job_staging_records`：采集结果与 admission 前状态。

不新增 LegacyJob/LegacyEvidence 平行 truth；不允许插件自行建表保存与 Core 冲突的职业身份。

---

## 6. API 与 SDK 验收契约

### 6.1 API

```text
GET    /api/v1/plugins
GET    /api/v1/plugins/catalog
POST   /api/v1/plugins/install-preview
POST   /api/v1/plugins/install
POST   /api/v1/plugins/{id}/enable
POST   /api/v1/plugins/{id}/disable
POST   /api/v1/plugins/{id}/healthcheck
POST   /api/v1/plugins/{id}/update-preview
POST   /api/v1/plugins/{id}/switch
POST   /api/v1/plugins/{id}/rollback
GET    /api/v1/plugins/{id}/audit

POST   /api/v1/knowledge/search
POST   /api/v1/knowledge/proposals/{id}/review
GET    /api/v1/wiki/pages/{id}/revisions

POST   /api/v1/jobs/search
POST   /api/v1/jobs/import
POST   /api/v1/jobs/staging/{id}/admit

POST   /api/v1/resume/patch-proposals
POST   /api/v1/resume/render
GET    /api/v1/resume/render-runs/{id}/ats-report
```

### 6.2 SDK 最小接口

```python
class Plugin:
    def manifest(self) -> PluginManifest: ...
    def health(self, ctx: PluginContext) -> HealthReport: ...
    def invoke(self, capability: str, request: dict, ctx: PluginContext) -> PluginEnvelope: ...
    def shutdown(self) -> None: ...
```

`PluginContext` 只提供 scoped Core client、Artifact client、logger、clock、secret handle 和 cancellation；不提供裸数据库连接、不提供整个用户目录、不提供未声明网络访问。

---

## 7. 安全、许可和数据治理

- 默认 localhost-only、token、最小权限和 deny-by-default 网络。
- 安装前执行 SPDX/license、依赖漏洞、secret pattern、可疑 install script、源码路径和网络域名扫描。
- 插件运行使用超时、并发、token/cost budget、大小限制、熔断和可取消任务。
- 外部职位描述视为不可信输入，不执行其中的指令、不自动访问其嵌入链接。
- 所有个人材料默认 local-first；发送到外部 LLM/KB 前显示目标、字段、保留期和脱敏选项。
- 审计记录包含插件版本、输入 hash、输出 hash、Evidence refs、用户决定和 rollback 点。

---

## 8. 交付切片与 Definition of Done

### Slice A — Plugin Foundation（先做）

- manifest/schema、registry、installation 状态机、permission gate、JSON envelope。
- `/plugins` 只读目录、安装预览、健康检查、审计页。
- 一个 `echo` worker plugin 和一个 `career-kb-local` adapter。
- migration、contract tests、失败/超时/回滚测试。

### Slice B — Career Knowledge

- local KB 导入、hybrid search、citation、proposal review、wiki revision/rollback。
- `career-kb-weknora` read-only adapter；没有 Core write bypass。

### Slice C — Resume Studio

- Base/Revision/Target、编辑器、预览、模板 registry、PDF、ATS report、人工 promotion。
- 至少一个自有模板和一个离线 fixture；不依赖 Magic Resume 源码。

### Slice D — Opportunity Radar

- manual URL/text source、一个离线 job-source fixture、dedupe、match/rank、staging/admission。
- 之后再接 JobSpy/WebMagic/portal skills，每个 source 单独审批和条款检查。

### Slice E — Lifecycle / Replacement

- update preview、shadow run、compatibility matrix、switch、rollback、backup/restore。
- Feishu/Gmail/Notion/ATS 等 external-write adapter 保持 proposal-only，直到用户单独授权。

### DoD

- 既有 v1.5 backend/frontend 回归全部通过，新增测试覆盖率和失败路径有记录。
- Core 数据库前后 hash、旧 read model、legacy archive/rehearsal 不被破坏。
- 每个插件都能被禁用，禁用后 Core 仍可启动、读取和导出。
- 每个生成结果都有 exact provenance；悬空引用 fail-loud。
- 安装、升级、替换、回滚均有可见审计记录和 deterministic fixture。
- 没有把 synthetic/browser interception 测试写成生产验收；真实外部动作单独标记 blocked/authorized。

---

## 9. 建议的首批插件目录

| 插件 ID | 类型 | 首期状态 |
|---|---|---|
| `career-kb-local` | builtin adapter | 必做 |
| `career-kb-weknora` | MCP/worker adapter | P1，读为主 |
| `resume-render-html` | builtin adapter | 必做 |
| `resume-render-latex` | worker plugin | P1 |
| `job-source-manual` | builtin adapter | 必做 |
| `job-source-jobspy` | worker adapter | P2，条款/限速后 |
| `job-source-webmagic` | worker adapter | P2，离线 fixture 先行 |
| `job-portal-ai-job-search` | CLI skill adapter | P2 |
| `application-reviewer` | LLM worker | P1，proposal-only |
| `feishu-projection` | projection plugin | 延续现有 offline-first |
| `gmail-signal` / `notion-projection` | external adapter | P3，默认只读/提案 |

---

## 10. 给 Codex 的开发提示词（可直接复制）

你正在维护 Agent Career Harness。请以仓库现状和本文 PRD 为约束，实施 v2.0 的 Slice A，不要一次性重写全系统。

### 开始前

1. 阅读现有状态文档、AGENTS.md、README、migrations、Core service、API wiring、AppShell、测试和 git diff。
2. 先输出一份“现状→目标差距表”和拟修改文件清单；不得假设计划已实现。
3. 保留 local-first、evidence-constrained、human-in-the-loop、stable Core / pluggable execution、replayable/auditable 原则。
4. 不执行 destructive cutover，不修改 Legacy 原件，不把第三方仓库源码复制进产品，不新增 LegacyJob/LegacyEvidence truth。

### 本轮实现范围（Slice A）

实现：

- Plugin Manifest v1 JSON schema 与 Python/TypeScript 类型。
- `PluginRegistry`、`PluginLifecycleManager`、`PermissionGate`、`PluginRunner`、`PluginEnvelope`。
- migrations 0014+（只添加插件包、版本、安装、权限、运行和更新计划；保持可逆）。
- Core service/API：列表、安装预览、启用/停用、healthcheck、update preview、rollback 记录。
- `/plugins` 桌面页面：列表、详情、权限、license、健康状态、审计和 disabled 状态。
- `echo` worker fixture plugin 与 `career-kb-local` read-only adapter。
- 失败、超时、取消、重复 request、未声明权限、悬空 evidence ref、回滚的测试。

不要在本轮：

- 连接真实 WeKnora、JobSpy、LinkedIn、ATS、Gmail、Feishu 外部写入。
- 自动安装任意 GitHub 仓库或运行其 install script。
- 实现无人审核的 Resume promotion、Capability promotion、Job admission 或投递。
- 修改现有 Resume/Projects 领域的 canonical 语义；只通过 adapter 接入。

### 设计要求

- 插件不得取得裸 SQLite 连接；只能使用 scoped Core/Artifact client。
- 默认 deny 网络、文件和 secret；权限必须来自 manifest 且经过 policy gate。
- 所有调用返回稳定 JSON envelope，含 request_id、plugin/version、status、input/output hash、warnings、evidence_refs 和 error code。
- 每次安装/启用/停用/升级/回滚写 DomainEvent + audit；重复调用必须幂等。
- 任何 proposal 都进入 review queue；任何 external_write capability 默认 blocked。
- 对第三方来源保存 repo、ref、immutable commit、license、scan report；许可证不明时只能 `quarantined`。
- API 错误 fail-loud，不能静默降级为猜测或假成功。

### 验证顺序

1. migration upgrade/downgrade 与 backup/restore rehearsal。
2. Plugin contract/unit/integration tests。
3. 现有 backend 全量回归、ruff、git diff --check。
4. frontend test/build 与既有视觉 baseline。
5. 用 echo plugin 做 install → enable → invoke → disable → rollback 的 deterministic acceptance。
6. 输出 changed files、迁移说明、测试结果、未完成项、风险和下一 Slice 建议。

如果遇到需要用户 authority、外部凭据、许可证解释或网站条款判断的地方，停止该分支并明确标记 `NEEDS USER AUTHORITY` 或 `BLOCKED_EXTERNAL_ACTION`，不要自行猜测。

### 后续 Slice 的执行顺序

完成并验收 Slice A 后，按 B（Career Knowledge）→ C（Resume Studio）→ D（Opportunity Radar）→ E（Lifecycle/Replacement）逐个提交小切片。每个切片都先写 contract/fixture/test，再写 adapter，再接 UI；不得把多个外部仓库一次性混进主分支。

---

## 11. 研究来源与实施备注

- Tencent/WeKnora：<https://github.com/Tencent/WeKnora>
- JOYCEQL/magic-resume：<https://github.com/JOYCEQL/magic-resume>
- webmagic-io/jobhunter：<https://github.com/webmagic-io/jobhunter>
- MadsLorentzen/ai-job-search：<https://github.com/MadsLorentzen/ai-job-search>
- Gsync/jobsync：<https://github.com/Gsync/jobsync>
- speedyapply/JobSpy：<https://github.com/speedyapply/JobSpy>

本 PRD 将外部项目视为参考实现或可隔离 adapter。进入发行物之前，仍需对当前 commit、许可证、依赖、网站条款、隐私边界和安全扫描结果进行一次实际复核。
