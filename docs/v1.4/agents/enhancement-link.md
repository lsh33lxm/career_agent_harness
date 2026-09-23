# SUBAGENT PROMPT — enhancement-link

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\enhancement-link
```

## Branch

```text
kimi/v14-enhancement-link
```

## Base Commit

```text
dfb82a6 docs: freeze enhancement task write path contract 0.4.1
```

## Workstream

```text
W2-ENHANCE-LINK（Project Enhancement Task 写路径 + canonical Gap 链接）
```

## Task

实现 Project Enhancement Task 的写路径，把 canonical Gap 与 enhancement task 接通：

1. 新建 `backend/career_harness/db/project_writes.py`：
   - `ProjectEnhancementTaskWrite`（实现 `TransactionalWrite` protocol，contract 字符串
     `project-enhancement-task-write-v1`）：创建任务（typed/generic revision 必须一致且为
     1）。`stage()` 内校验：
     - `project_id` 必须存在于 `project_identity`（fail loud）；
     - `target_gap_id` 必须解析到 canonical `match_gap` 行（fail loud on dangling——这是
       本 workstream 的核心，0004 的列没有 DB FK，写路径必须兜底）；
     - `target_capability_id` 必须等于该 Gap 行的 `capability_id`；
     - 新任务 status 必须为 `proposed`。
   - `ProjectEnhancementTaskStatusWrite`（contract
     `project-enhancement-task-status-write-v1`）：状态迁移命令，校验任务存在、
     typed/generic revision 一致、`expected_revision` 由 CommandService 保证；合法迁移集合
     用明确的白名单（例如 proposed→ready/in_progress/cancelled，
     in_progress→awaiting_validation/cancelled，awaiting_validation→completed/in_progress，
     取消/完成是终态）。非法迁移 fail loud。迁移只改 status + revision，不得改计划内容或
     target 引用（0004 已有 identity 稳定 trigger，写路径也要显式守住）。
2. 新建 `backend/career_harness/services/project_service.py`（或按现有 service 惯例命名）：
   - `propose_enhancement_task(command, *, task: ProjectEnhancementTask)`：经
     `CommandService.commit` 原子写 typed row + generic revision +
     `project_enhancement.proposed` event + idempotency。event payload 只含 metadata
     （task_id/project_id/target_gap_id/target_capability_id/status），不含计划内容本体。
   - `transition_enhancement_task(command, *, task_id, to_status)`：同上，event
     `project_enhancement.status_changed`。
   - 创建/迁移不得 mutate Gap、Match、Capability、Evidence 任何表（测试断言行数不变）。
3. 测试（`tests/integration/test_project_enhancement_service.py` 或按惯例）：
   - 创建成功路径（先 seed project + match_gap：可复用
     `tests/integration/test_match_service.py` 的 seed 模式）；
   - dangling target_gap_id fail loud 且整体回滚（entity_state/entity_revision/
     domain_event/idempotency/typed 行数不变）；
   - target_capability_id 与 Gap capability 不一致 fail loud；
   - 幂等重放返回首次结果；不同输入同 key → IdempotencyConflict；
   - 合法/非法状态迁移；revision 冲突；
   - canonical 表零 mutation 断言。

## Why This Task Exists

Match/Gap 垂直链路（policy `073d3d1`、persistence merge `b04d08e`、resolver/replay merge
`288ee30`）已合入，canonical Gap 可解析（`MatchRepository.get_gap`）。0004 的
`project_enhancement_task.target_gap_id` 列早于 Gap 表、没有 DB FK；契约 0.4.1 要求写路径
fail loud 校验。本任务接通 `Gap → Project Enhancement Task`，是纵向闭环
（Gap → Enhancement → Evidence → Resume）的下一环。

## Required Reading

```text
docs/v1.4/contracts.md                 # 0.4.1，Project evidence and enhancement 节
docs/v1.4/decision-log.md              # D-008, D-012, D-014
backend/career_harness/core/project/models.py   # ProjectEnhancementTask / status enum
backend/career_harness/db/models.py             # ProjectEnhancementTaskRow
migrations/versions/0004_project_evidence.py    # 表结构与 triggers
backend/career_harness/db/job_writes.py         # TransactionalWrite 模式
backend/career_harness/db/match_writes.py       # gap 校验写路径参照
backend/career_harness/services/match_service.py
backend/career_harness/services/command_service.py
backend/career_harness/db/project_repository.py # 既有 typed reads
tests/integration/test_match_service.py         # seed/测试模式参照
```

## Owned Paths

```text
backend/career_harness/db/project_writes.py                  # 新建
backend/career_harness/services/project_service.py           # 新建
tests/integration/test_project_enhancement_service.py        # 新建（或按惯例命名）
```

## Read-only Paths

```text
backend/career_harness/core/          # EntityKind.PROJECT_ENHANCEMENT_TASK 已由 Lead 加好
backend/career_harness/db/models.py   # 既有 ORM rows 只读
backend/career_harness/db/match_repository.py 等既有 repository
migrations/                           # 不需要新 migration；schema 能力足够
docs/
```

## Forbidden Paths

```text
apps/
importers/、D:\...\agent_rader
migrations/versions/                  # 缺 schema 能力就停下来发 CONTRACT CHANGE REQUEST
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.4.1`：创建即 `proposed`；target_gap_id 必须可解析且
capability 一致；状态迁移白名单；event payload 只含 metadata；不得 mutate 其他 canonical 表。

## Product Invariants

1. Local-first；Career Core 是 canonical truth。
2. Evidence != Fact != Signal != Decision != Outcome。
3. AI output 默认不是正式事实；enhancement task 是计划，不是 Fact。
4. SuggestedPriority 不能覆盖 UserPriority。
5. Official Capability Graph 与 Personal Capability Overlay 分离。
6. Project presence 不等于 personal mastery。
7. Coding Agent output 不能直接成为 Resume Fact。
8. Dangling provenance 必须 fail loud。
9. 任务创建/迁移不得触碰 Gap / Match / Capability / Evidence 表。

## Contract 不够用时

输出 `CONTRACT CHANGE REQUEST`（Current Contract / Problem / Proposed Change /
Affected Modules / Migration Impact / Backward Compatibility），不要私自另起模型。

## Implementation Rules

`reuse > incremental refactor > small new abstraction > rewrite`。禁止 Scope Creep。无关问题
记录为 `FOLLOW-UP`。

参考实现要点（写代码前仍需亲自核对）：

- `CommandService.commit()` 单事务协议与 `TransactionalWrite` 接口见
  `services/command_service.py`；`expected_revision` 冲突由它处理。
- `EntityKind.PROJECT_ENHANCEMENT_TASK` 已存在于 `core/common.py`（base commit 已含）。
- `ProjectEnhancementTaskRow` 在 `db/models.py`；0004 已有 identity 稳定 trigger 与
  status CHECK。
- `MatchGapRow` 在 `db/models.py`，写路径校验直接 `session.get(MatchGapRow, target_gap_id)`。

## Testing

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest tests/integration/test_project_enhancement_service.py -q
& $python -m pytest -q
& $ruff check backend tests migrations
& $ruff format --check backend tests
git diff --check
```

不要虚构测试结果。3 个已知 Windows symlink skip 不阻塞。

## Commit

review diff → 删除 debug code → 跑 tests → explicit stage（禁止 `git add .`）→ commit 到
`kimi/v14-enhancement-link`。建议 message：`feat: link enhancement tasks to canonical gaps`。
不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；核心行为有测试且全部通过；无 scope creep；未改 shared contract；未动
canonical data；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出（Workstream/Status/Branch/Commit/Changed Files/
Implemented/Tests Run/Test Results/Migration Impact/Contract Changes/Known Limitations/
Follow-up Tasks/Integration Notes）。

现在开始：inspect → implement → test → review diff → commit → report。
