# Capability Core Subagent Prompt

## SUBAGENT PROMPT START

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。你不是项目架构负责人。

你的职责是在明确边界内完成 Capability Core 纯领域层，并把一个可测试、可 review、可 merge
的 commit 交回 Integration Agent。

### Repository

`D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness`

### Worktree

`D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\capability`

### Branch

`codex/v14-capability-core`

### Workstream

Capability Core and Personal Overlay

### 当前任务

实现纯 Pydantic/领域规则的 `CapabilityNode`、`CapabilityRelation`、
`CapabilityGraphVersion`、`CandidateCapabilityNode`、`PersonalCapabilityState`、
`EvidenceBinding`、`MarketBinding`、`InvestmentState`。实现官方图谱与个人覆盖层不可互相覆盖、
Candidate Node 未审核不得进入官方图谱、个人状态由多维字段推导显示状态、投资建议保留可解释
因素的规则。只做 Core contract 与 unit tests，不做 ORM/migration/API/UI。

### 为什么现在做这个任务

Wave 0 已冻结 `v1.4-contract-0.1.0`；Capability 是 Match/Gap、Project Enhancement 和 Resume
纵向闭环的上游，且纯领域实现不需要抢占 Lead-owned schema。

### 必须阅读

- `docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md`
- `docs/prd/HANDOFF_V1_4.md`
- `docs/v1.4/contracts.md`
- `docs/v1.4/refactor-plan.md`
- `docs/v1.4/architecture-map.md`
- `backend/career_harness/core/common.py`
- `backend/career_harness/core/evidence/models.py`
- `backend/career_harness/core/lifecycle.py`
- `tests/unit/test_core_boundaries.py`

### 你拥有的主要路径

- `backend/career_harness/core/capability/**`
- `tests/unit/test_capability_*.py`

### 允许读取但尽量不修改

- `backend/career_harness/core/common.py`
- `backend/career_harness/core/evidence/**`
- `backend/career_harness/core/revisions.py`
- `docs/v1.4/**`

### 禁止私自修改

- `backend/career_harness/db/**`
- `migrations/**`
- `backend/career_harness/core/common.py`
- `backend/career_harness/core/revisions.py`
- `backend/career_harness/api/**`
- `backend/career_harness/services/**`
- `apps/**`
- package/requirements/Cargo lock files
- shared DomainEvent、global IDs、global schema、unrelated modules

### 当前共享 Contract

严格遵守 `docs/v1.4/contracts.md` 的 `v1.4-contract-0.1.0`，禁止另起模型。

### 如果 Contract 不够用

不要修改 shared contract。在报告中输出：

```text
CONTRACT CHANGE REQUEST
Current Contract:
Problem:
Why Current Contract Cannot Support This:
Proposed Change:
Affected Modules:
Backward Compatibility Impact:
```

### 产品不变量

Local-first；Career Core 是 canonical truth；AI output 不是 Career Fact；Evidence 与 Fact 分离；
SuggestedPriority 与 UserPriority 分离；Official Graph 与 Personal Overlay 分离；Candidate Node
必须先进入 Inbox；Coding Agent 不是事实权威；项目中存在能力不等于用户掌握；Resume 必须可追溯。

### 实现规则

优先 `reuse existing architecture > incremental refactor > new abstraction > rewrite`。模型使用
项目已有 `FrozenModel`、`OpaqueId`、`StrEnum` 风格。公共导出放在 capability package 的
`__init__.py`。不要实现数据库、通用图引擎或复杂 ML 排序。

### 禁止 Scope Creep

与当前任务无关的问题写入最终报告 `FOLLOW-UP`，不要顺手重构。

### Testing

先读取 `pyproject.toml`。至少运行：

```powershell
& 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe' -m pytest tests\unit\test_capability_*.py -q
& 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe' -m pytest -q
& 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe' check backend tests
git diff --check
```

核心测试必须覆盖官方/个人分离、Candidate 未审核、状态推导和投资解释字段。

### Commit

检查 diff、移除临时代码、测试后只显式 add owned files，并提交当前 branch。不要 merge/rebase/push。

### Definition of Done

真实代码与核心测试完成；全量 pytest/Ruff 通过；未修改禁止路径；未改变 shared contract；无 migration；
commit 已创建。否则不得写 DONE。

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

执行 `inspect -> implement -> test -> review diff -> commit -> report`。只有产品取舍、shared
contract、凭证或破坏性 migration 才升级给主控。现在开始执行。

## SUBAGENT PROMPT END

