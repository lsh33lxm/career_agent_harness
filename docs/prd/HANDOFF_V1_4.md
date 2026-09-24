# Agent Career Harness - v1.4 Engineering Handoff

**生成日期：** 2026-09-18
**范围：** 当前 repository 的只读工程盘点；未开始 PRD v1.4 重构。
**事实来源：** 当前 Git 工作树、源码、测试、架构/迁移文档、`docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md`。不以历史对话代替仓库事实。

> “已完成”只代表可在代码或历史验证中确认的基础能力，不代表对应 v1.4 产品闭环已交付。`UNKNOWN` 表示当前仓库无法证实。

## 当前工程状态

### Git snapshot

| 项目 | 事实 |
| --- | --- |
| 根目录 | `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness` |
| 分支 | `main` |
| HEAD | `567e3357b2cae5fe49e8d2b42ff8c00bf21c4292` |
| HEAD subject | `567e335 docs: record foundation and migration readiness` |
| 本地 branches / worktrees | 仅 `main` / 当前 worktree |
| 盘点时 tracked 改动 | 无 |
| 盘点时 untracked | `docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md` |

本文件是用户要求新建的交接材料，保存后也会成为 untracked，除非后续 Agent 决定提交。v1.4 PRD 不是本次 Agent 创建的代码变更，不能静默删除、覆盖或假定已经被 Git 追踪。

### 技术栈、目录和入口

| 层 | 当前实现 |
| --- | --- |
| Desktop | Tauri 2 / Rust 2021（最低 Rust `1.77.2`） |
| UI | React 19、TypeScript 5.9、Vite 7、React Router 7、Lucide、Vitest |
| Local API | Python >= 3.12、FastAPI、Pydantic v2、Uvicorn |
| Persistence | SQLite、SQLAlchemy 2、Alembic |
| 依赖 | npm workspace + `package-lock.json`；Python `requirements.lock` / `pyproject.toml`；Cargo.lock |

主要入口：

| 入口 | 文件 | 说明 |
| --- | --- | --- |
| Python API process | `backend/career_harness/__main__.py` | `python -m career_harness`；默认 `127.0.0.1:8765` |
| FastAPI app | `backend/career_harness/api/app.py` | 当前唯一业务面为 authenticated `GET /health` |
| React app | `apps/desktop/src/main.tsx` | 装载 `App.tsx` Router / error boundary |
| Tauri binary | `apps/desktop/src-tauri/src/main.rs` / `src/lib.rs` | 当前仅 desktop shell |
| Legacy importer CLI | `importers/agent_radar/__main__.py` | 只读 inventory/reconciliation |

目录分层为：`apps/desktop`（UI/Tauri）、`backend/career_harness`（API/Core/DB/storage/platform）、`importers/agent_radar`（legacy read-only）、`migrations`（Alembic）、`schemas`（legacy contract）、`tests/{unit,integration,contract}`、`docs/{adr,architecture,migration,prd}`。

### 启动、测试、build/lint/typecheck

当前没有可同时启动 Tauri、Python sidecar 和 DB bootstrap 的集成命令。开发时分别启动：

```powershell
# API：development 下须提供长度至少 16 的临时 token。
.\.venv\Scripts\python.exe -m career_harness --token <development-token>

# Web UI（127.0.0.1:5173）
npm --prefix apps/desktop run dev

# Tauri development shell；当前不启动 Python sidecar
npm --prefix apps/desktop run tauri dev

# Python test / lint
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check backend importers tests migrations

# Frontend test / TypeScript typecheck + production build
npm --prefix apps/desktop test
npm --prefix apps/desktop run build

# Rust/Tauri
cargo check --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
npm --prefix apps/desktop exec -- tauri build --debug --no-bundle

# Worktree check
git diff --check
git status --short --branch
```

`apps/desktop` 的 `build` 先运行 `tsc -b`，即当前 TypeScript typecheck。Python 没有独立 mypy/pyright 配置。API 拒绝 `0.0.0.0`；非 test 环境要求 Bearer token。前端能从 `window.__ACH_CONFIG__` 或 Vite env 读 URL/token，但 Tauri 没有注入这些值。

历史验证记录在 `GOAL_COMPLETION_REPORT.md`：Python `31 passed, 1 skipped`、frontend `4 passed`、Ruff/Vite/Cargo/Tauri debug build 均通过。Windows symlink fixture 因权限 skip。本次只写交接文档，未重跑完整套件。

### 用户数据、数据库和 migration

`backend/career_harness/platform/paths.py` 定义了目标数据根目录，但 app startup 尚未调用 `ensure_directories()` 或自动 bootstrap：

| 平台 | 目标根目录 |
| --- | --- |
| Windows | `%LOCALAPPDATA%\AgentCareerHarness` |
| macOS | `~/Library/Application Support/AgentCareerHarness` |
| Linux | `$XDG_DATA_HOME/agent-career-harness`，默认 `~/.local/share/agent-career-harness` |
| override | `ACH_DATA_DIR` |

目标布局为 `career_harness.db`、`artifacts/`、`backups/`、`browser-sessions/`、`logs/`。Alembic 默认仍指向 ignored 的 `./runtime/career_harness.db`，runtime wiring 未完成。PRD v1.4 中的 `AgentCareerHarnessData/core.db/sessions/extensions/project_evidence/references/context_exports` 尚未实现。

唯一 migration 是 `migrations/versions/0001_foundation.py`，创建：

- `entity_state`
- `entity_revision`
- `domain_event`
- `idempotency_record`
- `outbox_message`
- `migration_mismatch`

SQLite 不能被称为 legacy Agent Radar 历史的 canonical truth；reconciliation/cutover 仍未获批准。

## 当前已实现功能

| 模块 | 状态 | 实现与主要文件 |
| --- | --- | --- |
| Repo/docs foundation | 已完成 | `.gitignore`、`STATUS.md`、`ROADMAP.md`、`DECISIONS.md`、architecture/migration docs、ADR-013..016。后四项仍为 `PROPOSED`。 |
| Desktop app shell | 部分完成 | 十条路由、navigation、error boundary、health loading/offline：`apps/desktop/src/app/*`、`pages/*`。除 Today 外均 empty state。 |
| Today | Stub | `TodayPage.tsx` 只显示 health；日期硬编码 `Friday, September 18`，metrics / queue 固定为 0。 |
| Python Local API | 部分完成 | `api/app.py` 只有 token-protected `GET /health`、CORS、localhost guard；无领域 query/mutation API。 |
| Tauri | Stub | `src-tauri/src/lib.rs` 只有 default builder/run；无 sidecar、IPC、随机端口/token 注入。 |
| Core entities | 部分完成 | `core/lifecycle.py` 有 Candidate、Market、Opportunity、Resume、Application、Interview、Prep、Outcome、Approval、Run、Snapshot skeleton。 |
| Evidence / Fact boundary | 部分完成 | `core/evidence/models.py` 有 Artifact、Source、Snapshot、EvidenceRef、ExtractedClaim、Fact；隐式 promotion 明确抛错。无 table/repository/review command。 |
| Command/revision/event | 部分完成 | CommandService 原子写 current state、immutable revision、event、idempotency、optional outbox。未接 API/domain repository。 |
| LocalStepRunner | 已完成（基础） | `workflows/local_step_runner.py` 的 Protocol + sequential runner；不是 workflow engine。 |
| SQLite foundation | 已完成（基础） | `db/session.py`、`db/migrations.py`、`0001_foundation.py` 和 migration test。 |
| Artifact Store | 已完成（基础） | SHA-256 content-addressed filesystem store；拒绝 credential/session，未持久化 Artifact metadata。 |
| Backup/restore | 已完成（基础） | SQLite online backup、artifact hash manifest、integrity check、non-overwrite restore；有 integration test。 |
| Paths/secrets | 部分完成 | OS-aware AppPaths + redacting environment provider；不是 OS keychain，未接 runtime。 |
| Legacy Radar importer | 已完成（准备） | 只读 scan/hash/workbook metadata/manifest/reconciliation/output guard。无 Core import。 |
| Legacy reconciliation | 部分完成 | 结构和 deferred report 有；真实一次扫描有 332 deferred candidates，无 approved mapping/import/cutover。 |
| Browser worker / parser / LLM adapter | 未完成 | `adapters/`、`workers/` 只是空包/architecture 方向。 |
| Feishu companion | 未完成 | 仅 ADR/architecture 定位；无 adapter/API/write。 |
| Resume Patch / renderer | 未完成 | 只有空 `Resume` skeleton。 |
| Skill / MCP / extension runtime | 未完成 | 无 registry、capability resolution、manifest、runtime。 |
| Audit/event operations | 部分完成 | Event/outbox table/command write 已有；无 AuditLog、dispatcher、retry、query UI/API。 |

## 当前 Domain Model

| 对象 | 实际类型/持久化 | repository/service | API/IPC | 关系和约束 |
| --- | --- | --- | --- | --- |
| Artifact | Pydantic + files only，无表 | `ArtifactStore` | 无 | SHA-256、media/class/length；普通 store 拒绝 credentials/sessions。 |
| Source / SourceSnapshot / EvidenceRef | Pydantic only，无表 | 无 | 无 | Source -> Snapshot -> Artifact；EvidenceRef 指向 snapshot/artifact。 |
| ExtractedClaim | Pydantic only，无表 | 无 | 无 | 至少一条 evidence ref；proposed/accepted/rejected/superseded。 |
| Fact | Pydantic only，无专表 | 无 | 无 | authority、verified_by、revision；Claim 不可自动提升为 Fact。 |
| Project / Context / Signal / Decision | 未完成：无类型、表、repository、service 或 API | 无 | 无 | v1.4 所需显式对象；不能把规划中的对象误认为当前 `Market` 或 generic JSON 已实现。 |
| Candidate / Market / Resume / Prep / Outcome / Snapshot | 极轻 `DomainEntity` skeleton | 无 | 无 | 只有 id/revision/schema version；Snapshot 再有 input hash。 |
| Opportunity | Pydantic state enum；可塞 generic JSON，未接线 | 无 | 无 | discovered/watching/qualified/preparing/declined/expired/archived；无 JD/company/priority/match/gap。 |
| Application | Pydantic；可塞 generic JSON，未接线 | 无 | 无 | `opportunity_id`；非 preparing/ready 状态须 user confirmation 或 portal receipt。 |
| Interview / FormPreparation | Pydantic only，无表 | 无 | 无 | Interview -> application；FormPreparation -> opportunity；二者未串联。 |
| Approval | Pydantic；未接线 | 无 | 无 | final APPROVED 只能由 USER approver。 |
| Command / CurrentState / Revision / Event | Pydantic contracts + generic DB rows | `RevisionRepository` Protocol、`CommandService` | 无 | expected revision、immutable revision、idempotency 和 event。 |
| Outbox / Idempotency | ORM rows | `CommandService` | 无 | replay 返回相同 response；无 dispatcher。 |
| MigrationMismatch | ORM + importer reconciliation models | importer/reconcile | CLI report | source path/hash、legacy key、candidate id、disposition/reason。 |

已测试不变量：`ExtractedClaim != Fact`、`Opportunity != Application`、`Prepared != Submitted`、workflow state != business state、Agent 不可批准自己的 proposal、TEST data 不可进 PROD。

### 当前模型问题

1. `RevisionRepository.commit()` 声明返回 `CurrentState` 且需要 `event_type`，实际 `CommandService.commit()` 返回 `dict`、没有该参数。没有调用点掩盖了真实的 interface drift。
2. Pydantic `DomainEntity` 与 `entity_state.state` JSON blob 没有 mapper/repository。generic state table 是 substrate，不是完成的 domain schema。
3. v1.4 所需 Project、Context、Capability*、Resume*、Priority、Manifest 等均不存在为真实 type/table。
4. 当前 Opportunity enum 不等于 v1.4 funnel；`watching` 不是已实现的 Watchlist confirmation 流程。

## 当前实际架构决策

| 决策 | 现在实际采用的版本 |
| --- | --- |
| Local-first / canonical truth | Career Core 是新 Harness 数据的目标 truth owner；legacy history 在 approved reconciliation/cutover 前不是 SQLite truth。 |
| SQLite / Artifact Store | SQLite 放 generic current state/revisions/events；binary 用本地 SHA-256 store。两者尚没有 Artifact metadata linkage。 |
| Desktop/Feishu | Desktop 为 primary workspace；Feishu 为 companion/projection，不是 canonical DB。ADR-015 仍 `PROPOSED`。 |
| Browser Worker | 将来是 explicit worker/adapter，结果进入 Capture/Evidence contract；当前无 Playwright/browser code。 |
| LLM adapter | Provider-specific 逻辑不可进入 Core；当前无实现。 |
| Skill/MCP/adapter | v1.4 方向是 Skill 依赖 abstract Capability，extension 不拥有 truth；当前无 runtime。 |
| Resume Patch | 应基于 truth/evidence + user approval；当前未实现。 |
| Evidence/Fact | Artifact/Source/Snapshot/EvidenceRef/Claim 与 Fact 分型；需要显式 review/promotion。当前只有 type boundary。 |
| Audit/Event | current state + immutable revision + DomainEvent + transactional outbox，不是 event sourcing；dispatcher/query 缺失。 |
| UI -> Local API | 目标是 127.0.0.1 REST/JSON，random port + ephemeral token；当前开发固定端口/token，release injection/sidecar 未实现。 |

不要把 ADR-013/014/015/016 写成 “APPROVED”。它们是已记录方向，正式状态都是 `PROPOSED`。

## Current Implementation -> PRD v1.4 Gap

| PRD v1.4 | 当前状态 | 差距 |
| --- | --- | --- |
| 五类长期资产 | 部分完成（boundary only） | 有 Candidate/Market/Opportunity/Application/Outcome skeleton 与 Evidence primitives；无 Personal Context、Career State、Project Evidence、Target/Broad Market Evidence、Career History 的专用 schema/repository/query/UI。 |
| Context Compiler / Context Manifest | 未完成 | 无 selection/compression/vertical injection/manifest/Preview AI Context/AI context audit。 |
| Opportunity funnel | Stub | 仅 Opportunity enum；无 Broad Market/Discover/Watchlist/confirmed Opportunity/transition policy/JD source/company UI/API。 |
| Suggested Priority / User Priority | 未完成 | 无字段、reason、recompute、user override audit；不可用 Match/state 代替。 |
| Today Action Queue | Stub | UI 静态；无 action model、queue compiler、排序、deadline/follow-up/read API。 |
| Official Capability Graph | 未完成 | 无 CapabilityNode/Relation/GraphVersion/registry/ontology。 |
| Personal Capability Overlay | 未完成 | 无 CandidateCapabilityNode、PersonalCapabilityState、EvidenceBinding、MarketBinding/confirmation。 |
| Capability Inbox | 未完成 | 无 proposal review/accept/reject/versioning。 |
| Capability Investment Planning | 未完成 | 无 investment state、target market weighting、core roadmap/per-job tailoring/action generation。 |
| Project Evidence Library | 未完成 | 可复用 generic Artifact/Evidence primitives；无 Project、user scan scope、incremental scan、index/authority flow。 |
| Project Enhancement Loop | 未完成 | 无 project match/gap -> task -> rescan -> evidence loop。 |
| Project Enhancement Executor | 未完成 | 无 L1/L2/L3、worktree/allowed-path policy、CLI adapter、approval/merge control。现有 LocalStepRunner 不等于 executor。 |
| Resume Truth Model | 未完成 | Resume 是空 skeleton；无 ResumeBase/Patch/Revision/Render/truth linkage/approval。 |
| Career Reasoning | 未完成 | 无 decision/history/reasoning/priority/action explainability。 |
| v1.4 local data dir | 部分完成 | AppPaths 存在但名称/目录与 v1.4 `core.db` 等不一致，且未接启动 bootstrap。 |
| Extension / Skill / MCP | 未完成 | 无 capability registry、plugin/skill manifest 或 adapter implementation。 |
| Browser / Feishu / Coding executor | 仅定位文档 | 无 collector/projection/executor；不能把 PRD 角色描述当已实现能力。 |
| P0 Kernel | 部分完成 | Local Core substrate、SQLite、Artifact Store、basic event、package structure 有；Capability Registry、Context Compiler、Personal Context slice 缺失。 |

## 技术债、风险和已知 bug

### 高风险 / 容易 breaking

- `entity_state.state` 是无 per-entity schema/migration policy 的 JSON blob。新增 v1.4 对象前应先定 typed storage/repository strategy。
- Repository interface drift 必须先修或用 adapter 隔离。
- Opportunity lifecycle 需和 v1.4 对齐，但不得破坏 Opportunity/Application separation、Prepared/Submitted 和 user submission authority。
- UI config、Tauri、FastAPI、AppPaths、Alembic 是独立基础；任一单改可破坏 `/health` 体验。
- Legacy `SourceFile` filename key 只是候选，332 reconciliation rows 全 deferred，不可自动 canonicalize/import。

### 其他债务

- Today 日期硬编码，metrics/queue 静态；其它页面全是 placeholder。
- 没有领域 API、Tauri IPC、outbox dispatcher/retry/dead letter/AuditLog。
- ArtifactStore 无 metadata/reference count/retention；Backup/paths/importer 均未被 app startup 接线。
- EnvironmentSecretProvider 只有 `ACH_SECRET_*` redaction，无 OS keychain/rotation/runtime integration。
- `Application` validator 将除 `preparing`/`ready_for_review` 的所有状态视为 submitted-or-later；增新状态需显式调整。
- `RunState` 在 `core/lifecycle.py` 与 `workflows/local_step_runner.py` 重复定义。
- Windows symlink test 在当前权限下 skip；实现有防护，仍须在具备权限的 CI/release 环境复验。
- 仓库未发现 CI workflow、formatter 或 Python static type checker。外部 CI/packaging pipeline 为 `UNKNOWN`。
- `STATUS.md` 的 Last Verified Commit 仍为 `02fe966`，实际 HEAD 为 `567e335`，是文档 freshness debt。

## 重构中不得破坏的能力

1. API 只能 loopback；非 test 运行须 token，CORS `OPTIONS` 不得被 auth middleware 拦截。
2. Evidence/Fact、显式 promotion 和 provenance 不能退化为 LLM 自动写 Fact。
3. Opportunity 与 Application 不可合并；submitted authority 不可绕开。
4. expected revision、idempotency、immutable revision、DomainEvent 的单事务语义应保留。
5. ArtifactStore 的 content-addressing/atomic write/credential-session rejection，以及 browser sessions 分离。
6. Backup/restore 的 hash/integrity/non-overwrite 保证；新表/目录应加入其覆盖范围。
7. AppPaths 的 code/data separation 与 `ACH_DATA_DIR` override。
8. `agent_rader` 严格只读；importer 不跟随 link/reparse，输出不进入 legacy root。
9. `/health` 和 frontend health/offline state 可作为重构期 smoke-test compatibility surface。

## 推荐迁移顺序

以下仅基于当前代码结构，避免把交接文档替代 v1.4 产品设计。

1. **Contracts/runtime first：** 复核 v1.4 和 ADR，修正 repository drift，接通 AppPaths + migration bootstrap + Tauri sidecar/token config，保留 `/health` smoke test。
2. **Typed storage first：** 新 migration 引入 v1.4 explicit records，不继续把实体堆进 generic JSON；同时保持现有 revision/event/idempotency 兼容。
3. **Read boundary：** 提供 Today、Opportunity、Evidence/Project 的 read API，先把 static UI 变成 read-only projection。
4. **Opportunity vertical slice：** 先完成 Discover/Watchlist/Opportunity/Application transition、user confirmation、SuggestedPriority/UserPriority、audit，随后 Match/Gap/Today queue。
5. **Evidence + capability slice：** 基于现有 artifact/evidence/backup/runner 建 Project Evidence Library、official graph + personal overlay + inbox；自动输出保持 proposal。
6. **Executors/adapters last：** 审批、permissions、Context Manifest/audit 明确后才接 Coding executor/browser/LLM/Feishu；统一经 compatibility layer，不直写 Core。

| 处理 | 模块 |
| --- | --- |
| 可保留 | FastAPI auth/loopback、ArtifactStore、backup/restore、AppPaths、legacy importer、Pydantic invariant tests、Alembic foundation、Tauri CSP/capability config。 |
| 适合重构 | lifecycle skeleton、generic persistence 的领域映射、static pages、重复 RunState。 |
| 适合 compatibility layer | `/health`、frontend API config、CommandService 到新 repository、generic revision/event tables、legacy manifest/reconciliation schema。 |
| 不应扩张 | static metrics、placeholder page、filename-as-identity、把 architecture TODO 当 runtime implementation。 |
| migration 先决条件 | 先决定 DB bootstrap/schema ownership；再加 typed v1.4 entities；legacy import 仍只能在 approved disposable rehearsal 后做。 |

## Git 工作状态与 unfinished refactor

开始盘点时 `git status --short --branch` 为：

```text
## main
?? docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md
```

没有 staged/unstaged tracked changes、其他 branch 或 worktree。保存本文件后会有第二个 untracked 文件 `HANDOFF_V1_4.md`。本次没有运行 migration/import、legacy pipeline、Feishu write、ATS action 或 v1.4 重构。所谓 unfinished refactor 是尚未开始的 v1.4 vertical slices，不是工作树半改代码。

## Next Agent Start Here

首次进入先只读核验下列文件，再决定 worktree/subagent 拆分：

1. `HANDOFF_V1_4.md` 和 `git status --short --branch`：确认交接仍匹配当前树。
2. `docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md`：当前产品方向；先确认该未跟踪 PRD 的版本控制归属。
3. `AGENTS.md`：P0 范围、legacy read-only、编辑和提交约束。
4. `STATUS.md`、`GOAL_COMPLETION_REPORT.md`：foundation 验证记录及 status freshness debt。
5. `docs/architecture/SYSTEM_ARCHITECTURE.md`、ADR-013..016：分清已实现基础和仍 `PROPOSED` 的决定。
6. `backend/career_harness/services/command_service.py`、`core/repository.py`、`db/models.py`：优先解决 persistence contract drift / generic JSON 风险。
7. `core/evidence/models.py`、`core/lifecycle.py`：保留不变量并设计 typed v1.4 entities。
8. `apps/desktop/src/app/App.tsx`、`pages/TodayPage.tsx`、`src/api/client.ts`、`src-tauri/src/lib.rs`：确定最小 UI/API/sidecar vertical slice。
9. `migrations/versions/0001_foundation.py`、`platform/paths.py`：在加业务表前明确 DB bootstrap/migration。
10. `importers/agent_radar/`、`docs/migration/LEGACY_MIGRATION_PLAN.md`：仅需 legacy evidence 时使用，严格只读。

**第一项安全动作：** 运行 `git diff --check` 与 `git status --short --branch`，确认两个未跟踪文件的归属；随后先选择一个 typed Core + read API 的最小 P0 vertical slice。不要从 placeholder UI、真实浏览器投递、Feishu write、自动 legacy cutover 或 multi-agent runtime 开始。
