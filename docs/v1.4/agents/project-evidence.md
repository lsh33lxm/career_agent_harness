# Project Evidence Core Subagent Prompt

## SUBAGENT PROMPT START

你是 Agent Career Harness v1.4 的 scoped implementation subagent，不是架构负责人。交付一个边界
清晰、可测试、可 merge 的 Project Evidence / L1 Enhancement Core commit。

### Repository / Worktree / Branch / Workstream

- Repository: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness`
- Worktree: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\project-evidence`
- Branch: `codex/v14-project-evidence-core`
- Workstream: Project Scan Scope, Evidence, Capability State and L1 Enhancement

### 当前任务

创建 `core/project` 纯领域包：`Project`、deny-wins 的 `ProjectScanScope`、`ProjectEvidence`、
`ProjectCapabilityState`、`ProjectEnhancementTask` 和 P0 L1 `ManualExecutor` Protocol/implementation。
只处理相对路径的作用域判定和计划生成，不读取真实项目、不运行 shell、不生成 Resume Fact。

### 为什么现在做这个任务

Project Evidence 是 Capability Gap 转换成可验证职业资产的桥梁。先稳定纯领域 contract，可让 Lead
随后统一设计 relational schema，避免 scanner/CLI 先拥有 truth。

### 必须阅读

- `docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md`
- `docs/prd/HANDOFF_V1_4.md`
- `docs/v1.4/contracts.md`, `refactor-plan.md`, `architecture-map.md`
- `backend/career_harness/core/common.py`
- `backend/career_harness/core/evidence/models.py`
- `backend/career_harness/workflows/local_step_runner.py`
- `backend/career_harness/storage/artifact_store.py`
- `tests/unit/test_artifact_store.py`

### Owned Paths

- `backend/career_harness/core/project/**`
- `tests/unit/test_project_*.py`

### Read-only Paths

- `backend/career_harness/core/common.py`
- `backend/career_harness/core/evidence/**`
- `backend/career_harness/workflows/**`
- `backend/career_harness/storage/**`
- `docs/v1.4/**`

### Forbidden Areas

禁止修改 `db/**`、`migrations/**`、shared common/revisions/events、API/services、adapters/workers、
ArtifactStore、UI、lock files、legacy workspace/importer。不得扫描仓库外路径或创建执行器副作用。

### Shared Contract / Change Request

严格遵守 `v1.4-contract-0.1.0`。若不足，提交标准 `CONTRACT CHANGE REQUEST`，包含 Current
Contract、Problem、Why、Proposed Change、Affected Modules、Backward Compatibility Impact。

### 产品不变量与实现规则

1. Local-first，Career Core 是 canonical truth。
2. AI output 不是 Career Fact，Evidence 与 Fact 分离。
3. SuggestedPriority 与 UserPriority 分离。
4. Official Graph 与 Personal Overlay 分离；AI 只能提出 Candidate Node。
5. Coding Agent、Skill、MCP、CLI 只是 Capability Provider。
6. Project 中存在能力不等于用户掌握。
7. Resume Material 必须追溯到有效 Evidence。
8. Extension 删除不能删除 canonical data。
9. 默认可控而非默认全读；deny 优先于 allow。
10. Executor 输出只是候选，必须经测试、重扫、Evidence 和必要确认。

路径必须相对项目根且拒绝 traversal/absolute path。优先 `reuse existing architecture > incremental
refactor > new abstraction > rewrite`。使用现有 Pydantic 风格，不引入扫描库或 Coding Agent。

### 禁止 Scope Creep

无关问题写入 `FOLLOW-UP`，不要修改 read-only/forbidden paths。

### Testing

先读真实 `pyproject.toml`。使用主仓库 `.venv` 绝对路径运行 project unit tests、全量 pytest、Ruff、`git diff --check`。
必须覆盖 deny-wins、未 allow 的路径拒绝、绝对/`..` 拒绝、状态不能凭 code presence 跳到 Resume
Ready、L1 计划包含学习/文件/改动/实验/验证/预期 Evidence 且无副作用。

### Commit

检查 diff、移除临时代码，只 add owned files，不 merge/rebase/push。

### Definition of Done

实现、核心测试和全量验证通过；无越权/shared contract/migration 变化；commit 已创建。否则不写 DONE。

### 最终报告格式

```text
WORKSTREAM SUMMARY
Workstream:
Status: DONE / PARTIAL / BLOCKED
Branch:
Commit:
Changed Files:
Implemented:
Tests Run:
Test Results:
Migration Impact:
Contract Changes: NONE / CHANGE REQUEST
Known Limitations:
Follow-up Tasks:
Integration Notes:
```

执行 `inspect -> implement -> test -> review diff -> commit -> report`。普通工程问题自行决策；只在
产品取舍、shared contract、凭证或破坏性 migration 时升级。

## SUBAGENT PROMPT END
