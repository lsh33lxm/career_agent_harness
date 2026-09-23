# SUBAGENT PROMPT — today-read-core

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\today-read-core
```

## Branch

```text
kimi/v14-today-read-core
```

## Base Commit

```text
16baf32 docs: freeze today read model contract 0.8.0
```

## Workstream

```text
NEXT READY #1/#3 的 Core 半区：Today Read Model（纯 read model，不含前端替换）
```

## Task

实现 Core-owned Today Read Model（后端 only；前端 fallback 替换是后续 workstream）：

1. 新建 `backend/career_harness/core/today/`（`models.py` + `__init__.py`）：
   - `TodayItemKind`：`OPPORTUNITY_ACTION` / `APPLICATION_STEP` / `INTERVIEW_PREP` /
     `ENHANCEMENT_TASK` / `REVIEW_REQUEST`（封闭集合，对齐契约 0.8.0）。
   - `TodayReasonCode`：typed reason codes（如 USER_PRIORITY_HIGH、SUGGESTED_PRIORITY_URGENT、
     DEADLINE_APPROACHING、INTERVIEW_UPCOMING、PENDING_USER_REVIEW、GAP_LINKED_TASK、
     MISSING_USER_PRIORITY 等，按实现需要定，但必须 typed）。
   - `TodayItem`：稳定 deterministic `item_id`（由 kind + source entity id 派生，例如
     `today:<kind>:<entity_id>`）、kind、source refs（entity id + revision）、reasons、
     使用的 priority 输入、排序键所需的 deadline/interview 时间。
   - `TodayQueue`：items（有序）、input_revisions（本次计算用到的 exact revision 集）、
     generated_at、policy_version（`today-policy-v1`）。
2. 纯函数 policy（建议 `core/today/policy.py` 或 services 层纯函数）：从 typed 输入计算
   TodayQueue。排序必须是契约 0.8.0 的 total order：user priority rank → suggested
   priority rank → 最早 deadline/interview → item_id tiebreak。缺失输入显式落入最低 bucket
   并带 reason code；不编造数据；空输入出空队列。
3. `services/today_service.py`（或按现有惯例）：从既有 repository 读（Opportunity list +
   priorities、Application、enhancement tasks、待 review 的 requirement/claim/resume patch
   proposals），组装 typed 输入并调用 policy。**纯读**：不得写任何表，不得重算/写
   SuggestedPriority，不得改 UserPriority。缺数据时按契约显式降级。
4. 认证 Local API：`GET /today`（对齐 `api/opportunities.py` 的认证与错误处理模式），
   返回 TodayQueue 的可序列化形式。空库/无权限行为明确。
5. 测试：
   - policy 单测：排序 total order（含乱序输入等价）、缺失 priority/deadline 的显式降级、
     reason codes、稳定 item_id、空输入；
   - service 集成测试（disposable DB）：多源数据组装、只读断言（所有写表行数不变）；
   - API 测试：认证失败 401/403、空队列、正常返回。

## Why This Task Exists

Today 页目前渲染静态 typed fallback（`apps/desktop/src/pages/today/data.ts`），可能与
canonical truth 漂移。契约 0.8.0（`docs/v1.4/contracts.md` "Today read model" 节）与 D-017
已冻结：Today 是 Core-owned deterministic projection，不落表、不写任何东西、客户端不排名。

## Required Reading

```text
docs/v1.4/contracts.md                 # 0.8.0 Today read model 节
docs/v1.4/decision-log.md              # D-017
docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md  # §8 Today、§23.1
docs/v1.4/HANDOFF_CODEX_TO_KIMI_2026-09-20.md    # H/K/L 节（本任务来源）
backend/career_harness/api/opportunities.py      # 认证 API 模式
backend/career_harness/api/app.py                # router 挂载
backend/career_harness/db/opportunity_repository.py
backend/career_harness/db/project_repository.py  # enhancement task reads
backend/career_harness/db/fact_repository.py     # claim review 状态
backend/career_harness/db/resume_repository.py   # patch review 状态
backend/career_harness/db/job_repository.py      # requirement review 状态
backend/career_harness/db/ 下的 application repository（Codex 新增，自行定位）
```

## Owned Paths

```text
backend/career_harness/core/today/            # 新建
backend/career_harness/services/today_service.py   # 新建
backend/career_harness/api/today.py           # 新建
tests/ 下新增 today 相关测试                   # 新建
```

追加式修改（只追加、不改既有逻辑）：

```text
backend/career_harness/api/app.py             # 只挂载新 router
```

## Read-only Paths

```text
backend/career_harness/core/（today/ 以外）
backend/career_harness/db/                    # repository 只读使用；缺 read 发 CONTRACT CHANGE REQUEST
migrations/                                   # 不需要新 migration（read model 不落表）
apps/                                         # 前端替换是后续 workstream
docs/
```

## Forbidden Paths

```text
apps/
importers/、D:\...\agent_rader
migrations/versions/
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.8.0` "Today read model" 节。关键不变量：

- Today 是纯 projection：零写入、零 mutation；重算队列永不动 UserPriority。
- item kind 封闭集合；排序 total order 确定；缺失输入显式降级带 reason code。
- response 携带 input revision set；空输入出空队列，不编造。
- ranking 逻辑不得出现在客户端（本 workstream 不动前端）。

## Product Invariants

1. Local-first；Career Core 是 canonical truth。
2. Evidence != Fact != Signal != Decision != Outcome。
3. SuggestedPriority != UserPriority；重算永不动 UserPriority。
4. Match != Priority。
5. Latest-at-read 对 Today 是允许的（它是当前投影而非历史 replay），但 response 必须携带
   input revisions 供 staleness 检测。
6. 不引入 synthetic 评分百分比。

## Contract 不够用时

输出 `CONTRACT CHANGE REQUEST`，不要私自另起模型。

## Implementation Rules

`reuse > incremental refactor > small new abstraction > rewrite`。禁止 Scope Creep。无关问题
记录为 `FOLLOW-UP`。

## Testing

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest <focused> -q
& $python -m pytest -q
& $ruff check backend tests migrations
& $ruff format --check backend tests
git diff --check
```

不要虚构测试结果。3 个已知 Windows symlink skip 不阻塞。

## Commit

review diff → 删除 debug code → 跑 tests → explicit stage（禁止 `git add .`）→ commit 到
`kimi/v14-today-read-core`。建议 message：`feat: add core today read model`。
不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；policy/service/API 核心行为有测试且全部通过；零写入有断言；无 scope creep；
未改 shared contract；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出（Workstream/Status/Branch/Commit/Changed Files/
Implemented/Tests Run/Test Results/Migration Impact/Contract Changes/Known Limitations/
Follow-up Tasks/Integration Notes）。

现在开始：inspect → implement → test → review diff → commit → report。
