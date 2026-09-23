# SUBAGENT PROMPT — interview-core

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\interview-core
```

## Branch

```text
kimi/v14-interview-core
```

## Base Commit

```text
{worktree 创建时的 integration HEAD；git log --oneline -1 确认}
```

## Workstream

```text
P1：Interview 记录持久化（契约 0.11.0 + D-021）
```

## Task

实现 Interview 的持久化与显式生命周期命令：

1. 先 inspect 现状：`core/lifecycle.py`（Interview skeleton）、`db/models.py`、migration 0012
   （Application/Outcome 表与 trigger 风格）、`services/application_service.py`、
   `db/` 下 Codex 新增的 application repository/writes（自行定位）。
2. core 模型：`core/lifecycle.py` 的 `Interview` 只有 application_id。在其所属模块（或按
   现有 core 结构新建 `core/interview/models.py`，按现状惯例选择）补全 Interview 模型：
   interview_id、application ref（exact application_id + revision）、round
   （screen/technical/loop/offer_talk）、scheduled_at、status
   （scheduled/completed/cancelled）、evidence_refs（exact，可为空）、revision、
   schema_version、created_at/by。status 默认值与 review 字段校验参照既有模式。
   （若改 lifecycle.py 的既有 Interview 类会破坏既有调用，则新建模块并保留兼容导出。）
3. additive migration `0013_interview_core`（down_revision = 0012）：interview 表
   （identity + revision 风格对齐 0012；round/status CHECK；immutable history + identity
   稳定 triggers；FK 到 application 表按 0012 实际结构）。upgrade/downgrade 对称，disposable
   DB 验证 `0012 -> 0013 -> 0012 -> 0013`。
4. `db/models.py` 只追加 ORM rows；`db/interview_repository.py` typed reads（exact/latest、
   list_for_application 稳定排序）；`db/interview_writes.py` + `services/interview_service.py`：
   - `schedule_interview`（user 或 agent）：application 必须存在且处于 submitted-or-later
     之前的任意非终态（具体边界按 0012 的 Application 状态机核对；若契约未覆盖某边界，按
     最保守解释并在报告中说明）；
   - `complete_interview` / `cancel_interview`：显式状态迁移命令，revision 连续；
   - 事件 `interview.scheduled` / `interview.completed` / `interview.cancelled`，payload
     纯 metadata；全部经 `CommandService.commit` 原子写；
   - 永不创建或暗示 Outcome；永不 mutate Application/Resume/Fact/Match/priorities（测试断言）。
5. 测试：schedule/complete/cancel 成功路径；dangling application fail loud；非法迁移 fail
   loud；幂等重放；原子回滚；migration rehearsal；不碰其他域断言。

## Why This Task Exists

契约 0.11.0 + D-021 已冻结 Interview 语义。Interview 目前只有 skeleton；它是
Application → Interview → Outcome 链路与 Today 排序（interview 时间维度）的前置。

## Required Reading

```text
docs/v1.4/contracts.md            # 0.11.0 Interview records 节
docs/v1.4/decision-log.md         # D-017（Application/Outcome）, D-021
backend/career_harness/core/lifecycle.py
migrations/versions/0012_application_outcome.py
backend/career_harness/db/models.py（Application/Outcome rows）
backend/career_harness/services/application_service.py
backend/career_harness/services/command_service.py
tests/ 下 Application/Outcome 的既有测试（自行定位，参照其 seed 模式）
```

## Owned Paths

```text
backend/career_harness/core/interview/（如新建）或 core/lifecycle.py 的 Interview 补全
migrations/versions/0013_interview_core.py     # 新建
backend/career_harness/db/interview_repository.py  # 新建
backend/career_harness/db/interview_writes.py      # 新建
backend/career_harness/services/interview_service.py  # 新建
tests/ 下新增 interview 测试                        # 新建
```

追加式修改（只追加、不改既有逻辑）：

```text
backend/career_harness/db/models.py   # 只追加 ORM rows
```

## Read-only Paths

```text
backend/career_harness/core/（interview 模型补全除外）
migrations/versions/0001..0012
apps/
docs/
```

## Forbidden Paths

```text
apps/
importers/、D:\...\agent_rader
migrations/versions/0001..0012
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.11.0`：Interview 永不创建/暗示 Outcome；显式生命周期
命令；revision 连续；payload 纯 metadata；不碰其他域。

## Product Invariants

1. Local-first；Career Core 是 canonical truth。
2. Evidence != Fact != Signal != Decision != Outcome。
3. Workflow State != Business State。
4. Dangling provenance fail loud。
5. AI-drafted prep content is a proposal, never truth。

## Contract 不够用时

输出 `CONTRACT CHANGE REQUEST`，不要私自另起模型。

## Implementation Rules

`reuse > incremental refactor > small new abstraction > rewrite`。禁止 Scope Creep。

## Testing

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest <focused> -q
& $python -m pytest -q
& $ruff check backend tests migrations
& $ruff format --check backend tests migrations
git diff --check
```

不要虚构测试结果。3 个已知 Windows symlink skip 不阻塞。

## Commit

explicit stage（禁止 `git add .`）→ commit 到 `kimi/v14-interview-core`。建议 message：
`feat: add interview records and lifecycle`。不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；核心行为有测试且全部通过；migration rehearsal 通过；无 scope creep；未改
shared contract；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出。

现在开始：inspect → implement → test → review diff → commit → report。
