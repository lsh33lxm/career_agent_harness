# SUBAGENT PROMPT START

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是项目架构负责人。你的职责是：

> 在明确边界内完成 Project Capability State/Basis 与 Project Enhancement Task typed reads，
> 并把一个可测试、可 review、可 merge 的 commit 交回 Integration Agent。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\project-state-read
```

## Branch

```text
codex/v14-project-state-read
```

## Workstream

```text
Project Capability State and Enhancement Task typed reads
```

## 当前任务

扩展现有 `ProjectRepository`，只实现 read path：

1. `get_project_capability_state(capability_state_id, revision=None)`：exact 或单 identity latest。
2. `list_project_capability_states(project_id, capability_id=None, latest_only=True)`：返回确定性
   排序，latest-only 必须按每个 `capability_state_id` 分组，不得按 project/capability 混选。
3. 重建每个 state 的完整 relational basis，保留 exact reference revision，并映射 DB
   `finalized_at` 到 Core contract。
4. `get_enhancement_task(task_id, revision=None)`：exact 或单 task identity latest。
5. `list_enhancement_tasks(project_id, target_gap_id=None, latest_only=True)`：确定性排序并按
   task identity 选择 latest。
6. missing exact/latest 返回 `None` 或空 tuple，不回退到其他 identity/revision。
7. 不实现 writes、Match/Gap、scanner、API 或 schema change。

## 为什么现在做这个任务

P0 Match/Gap 需要 exact Project Capability inputs 来判断“项目接近程度”，但项目中存在代码不
等于用户掌握。当前 schema/Core 已有 state、basis 和 L1 task，repository 尚未暴露。该 read
workstream 与 JobRequirement Core 独立，可以并行，且不会修改 shared schema。

## 必须阅读

```text
AGENT_CAREER_HARNESS_PRD_v1.2.md
docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md
docs/prd/HANDOFF_V1_4.md
docs/v1.4/contracts.md
docs/v1.4/refactor-plan.md
docs/v1.4/architecture-map.md
backend/career_harness/core/project/models.py
backend/career_harness/core/project/__init__.py
backend/career_harness/db/models.py
backend/career_harness/db/project_repository.py
migrations/versions/0004_project_evidence.py
tests/integration/test_project_repository.py
tests/unit/test_project_evidence.py
tests/unit/test_project_enhancement.py
```

## 你拥有的主要路径

```text
backend/career_harness/db/project_repository.py
tests/integration/test_project_repository.py
```

## 允许读取但尽量不修改

```text
backend/career_harness/core/project/**
backend/career_harness/db/models.py
migrations/versions/0004_project_evidence.py
docs/v1.4/**
```

## 禁止私自修改

默认包括：

```text
global database schema
shared domain IDs
global migrations
shared DomainEvent definitions
core API / IPC contracts
unrelated modules
package lock
```

具体禁止：

```text
backend/career_harness/core/**
backend/career_harness/services/**
backend/career_harness/db/models.py
migrations/**
apps/**
docs/v1.4/contracts.md
docs/v1.4/refactor-plan.md
STATUS.md
package-lock.json
requirements.lock
```

## 当前共享 Contract

严格遵守 `docs/v1.4/contracts.md` 的 `v1.4-contract-0.3.0`。`ProjectCapabilityState` 已正式
包含 `finalized_at`，不得创建 repository-only envelope 或第二套 domain model。

## 如果 Contract 不够用

不要偷偷修改 shared contract。在最终报告输出：

```text
CONTRACT CHANGE REQUEST

Current Contract:

Problem:

Why Current Contract Cannot Support This:

Proposed Change:

Affected Modules:

Backward Compatibility Impact:
```

主控决定是否修改。

## 产品不变量

1. Local-first。
2. Career Core 是 canonical truth。
3. AI output 默认不是正式 Career Fact。
4. Evidence 与 Fact 必须区分。
5. SuggestedPriority 与 UserPriority 必须区分。
6. UserPriority 不能自动覆盖。
7. Official Capability Graph 与 Personal Capability Overlay 必须逻辑分离。
8. AI 可以发现 Candidate Capability Node，但不能随意修改正式 Ontology。
9. Coding Agent / Skill / MCP / CLI 都只是 Capability Provider。
10. Project 中存在某能力，不等于用户掌握。
11. Resume Material 必须可以追溯到有效 Evidence。
12. Extension 删除后 canonical data 不能丢失。

## 实现规则

优先复用 `ProjectRepository._get_revisioned_row` 和既有 mapper 风格。可以最小泛化其类型，
但不要引入新 repository abstraction。Basis 从 relational rows 重建；排序必须显式稳定。

## 禁止 Scope Creep

不要修改 scanner、安全策略、Core model、schema/migration、write service、Match/Gap、API/UI。
发现其他问题写入 `FOLLOW-UP` 交回主控。

## Testing

先读取真实 build config。测试至少覆盖：

- capability state exact/latest 隔离；
- 同 project/capability 多个 state identity 不串历史；
- latest-only 与完整 history 的确定性排序；
- basis kind/reference ID/revision 完整且稳定；
- `finalized_at` 不丢失；
- enhancement task exact/latest、project/target gap filters；
- missing identity/revision 返回 None/empty；
- malformed persisted aggregate fail loud，不静默丢 basis。

运行真实适用的 focused/full pytest、Ruff 和 `git diff --check`。

## Commit

实现完成后检查 diff、移除 debug/temp code、跑测试并 commit 当前 branch。Commit message 应
清晰表达 Project typed read workstream。

## Definition of Done

只有以下条件满足才能写 DONE：

```text
真实代码实现完成
核心行为有测试
exact/latest 与 grouping 正确
basis revisions/finalized_at 不丢失
focused/full pytest 通过
Ruff 通过
没有修改无关模块
没有 shared contract/schema/migration change
commit 已创建
```

## 最终报告格式

```text
WORKSTREAM SUMMARY

Workstream:

Status:
DONE / PARTIAL / BLOCKED

Branch:

Commit:

Changed Files:

Implemented:

Tests Run:

Test Results:

Migration Impact:

Contract Changes:
NONE / CHANGE REQUEST

Known Limitations:

Follow-up Tasks:

Integration Notes:
```

如果不是完全完成，不要写 DONE。

## 工作方式

```text
inspect
-> implement
-> test
-> review diff
-> commit
-> report
```

普通工程问题自行合理决策。只有产品取舍、shared contract 修改、外部凭证或破坏性 migration
才升级给主控。现在开始执行。

# SUBAGENT PROMPT END
