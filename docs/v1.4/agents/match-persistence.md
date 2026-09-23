# SUBAGENT PROMPT — match-persistence

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\match-persistence
```

## Branch

```text
kimi/v14-match-persistence
```

## Base Commit

```text
08f1548 docs: freeze match persistence resolver and replay contracts
```

## Workstream

```text
W2-MATCH-PERSIST（persistence 半区）
```

## Task

实现 durable Match/Gap persistence 的持久化半区（不含 resolver/replay 编排）：

1. 新增 additive migration `migrations/versions/0009_match_gap_persistence.py`：
   - `match_assessment`：Core 生成 `assessment_id` PK；`opportunity_id` +
     `opportunity_revision`；`job_id` + `job_revision`；`candidate_id`；`policy_version`；
     `manifest`（canonical JSON snapshot， bounded immutable payload）；`created_at` /
     `created_by`。immutable triggers（BEFORE UPDATE/DELETE RAISE ABORT），风格对齐 0008。
   - `match_requirement_result`：`(assessment_id, requirement_id, requirement_revision)` 复合
     PK；`capability_id`；`classification`（covered/quick_to_strengthen/clear_gap）；
     `covered_scopes` / `missing_scopes`（bounded JSON 数组）；`reasons`（bounded JSON
     payload）。immutable triggers。
   - `match_gap`：`gap_id` PK（Core 生成）；`assessment_id`；`requirement_id` +
     `requirement_revision`；`capability_id`；`classification`（只允许
     quick_to_strengthen / clear_gap，用 CHECK 约束）；immutable triggers。
   - upgrade/downgrade 对称；在 disposable DB 上验证 `0008 -> 0009 -> 0008 -> 0009`。
2. `backend/career_harness/db/models.py` 追加 ORM rows（只追加，不改既有 rows）。
3. 新增 `backend/career_harness/db/match_repository.py` typed reads：
   - `get_assessment(assessment_id)` → 聚合（assessment + manifest + results + gaps），
     缺失返回 None，malformed 数据 fail loud（对齐 EvidenceRepository 风格）；
   - `get_gap(gap_id)`；`list_gaps_for_assessment(assessment_id)`；
   - `list_assessments_for_opportunity(opportunity_id)`（按 created_at/assessment_id 稳定
     排序，供"最新 assessment"查询，但 replay 不得依赖它）。
4. 新增 `backend/career_harness/db/match_writes.py`：`MatchAssessmentWrite` 实现
   `TransactionalWrite` protocol（`idempotency_payload()` + `stage()`），stage 内校验：
   - manifest 与 assessment 头部一致（opportunity/job/policy_version）；
   - 每条 result 的 `(requirement_id, revision)` 必须存在于 `job_requirement_revision`
     且属于冻结的 Job revision，scopes 划分与契约一致；
   - gap 只能为非 COVERED result 生成，`gap_id` 唯一；
   - 先子行后主行或反之必须与触发器一致，整体失败全部回滚。
5. 新增 `backend/career_harness/services/match_service.py`：
   - `MatchService.record_assessment(...)`：接收已经由 pure policy
     (`career_harness.core.match_gap.assess_match`) 产出的 `MatchAssessment`，通过
     `CommandService.commit(...)` 原子写入 typed rows + generic revision +
     `match.assessed` event（payload 只含 ids/revisions/policy_version/各 classification
     计数）+ idempotency。事件 payload 不得覆盖 Core 生成的 `revision_id`。
   - 本 workstream 不实现 resolver / replay / assess 编排（那是后续 workstream）。
6. `backend/career_harness/db/opportunity_repository.py` 新增 exact read：
   - `get_revision(opportunity_id, revision) -> OpportunityDetail | None`，只追加方法，
     不改变既有 `get()` 语义。

## Why This Task Exists

Pure Match/Gap policy 已在 `073d3d1` 合入并通过 final review。当前缺口：没有 durable
MatchAssessment/Gap schema，`ProjectEnhancementTask.target_gap_id` 没有可解析的 canonical
Gap record，历史 Match 无法跨进程 replay。契约已在 `docs/v1.4/contracts.md` `0.4.0` 冻结
（Match persistence / Match resolver and replay 两节）及 decision-log D-014。resolver +
replay 编排是后续串行 workstream，不在本任务内。

## Required Reading

```text
docs/v1.4/contracts.md                       # 0.4.0，Match persistence/resolver/replay 节
docs/v1.4/decision-log.md                    # D-012, D-013, D-014
docs/v1.4/migration-plan.md                  # M3e 与 required migration tests
backend/career_harness/core/match_gap/       # pure policy（models.py / policy.py）
```

另外阅读（既有模式，严格对齐）：

```text
migrations/versions/0008_job_requirement_persistence.py   # 表/trigger 风格
migrations/versions/0007_evidence_provenance.py           # immutable trigger 生成器
backend/career_harness/db/job_repository.py               # typed read 模式
backend/career_harness/db/job_writes.py                   # TransactionalWrite staging 模式
backend/career_harness/db/evidence_repository.py          # fail-loud 聚合读
backend/career_harness/services/job_service.py            # command service 编排
backend/career_harness/services/command_service.py        # commit 事务协议
backend/career_harness/db/opportunity_repository.py       # get() 现状
tests/unit/test_match_policy.py                           # policy 行为基线
```

## Owned Paths

```text
migrations/versions/0009_match_gap_persistence.py        # 新建
backend/career_harness/db/match_repository.py            # 新建
backend/career_harness/db/match_writes.py                # 新建
backend/career_harness/services/match_service.py         # 新建
tests/unit/test_match_persistence.py（或按现有测试目录惯例命名/拆分）  # 新建
tests/ 下新增 migration 0009 测试                          # 新建
```

追加式修改（只追加、不改既有逻辑）：

```text
backend/career_harness/db/models.py                      # 只追加 ORM rows
backend/career_harness/db/opportunity_repository.py      # 只追加 get_revision
```

## Read-only Paths

```text
backend/career_harness/core/                             # 全部只读
backend/career_harness/services/command_service.py
backend/career_harness/services/job_service.py
migrations/versions/0001..0008
docs/
```

## Forbidden Paths

```text
apps/                                 # 不动前端
importers/、D:\...\agent_rader         # legacy 只读
migrations/versions/0001..0008        # 不改历史 migration
backend/career_harness/db/job_repository.py、job_writes.py、capability_repository.py、
project_repository.py、evidence_repository.py   # 不改既有 repository
```

## Shared Contract

必须严格遵守 `docs/v1.4/contracts.md` `0.4.0`。不要另起模型。关键冻结点：

- assessment 不可变、单 revision；重新评估 = 新 assessment。
- manifest JSON snapshot 是唯一 replay 源；typed result/gap rows 保证可查询性。
- gap 只为 QUICK_TO_STRENGTHEN / CLEAR_GAP 生成，immutable，新 assessment 铸新 gap。
- `target_gap_id` 在本 workstream 不加 DB FK（列早于 gap 表）；写路径 fail loud 由后续
  enhancement 写路径负责，本任务只需保证 `get_gap` 可解析。
- event payload 只放 metadata（ids/revisions/policy_version/counts）。

## Product Invariants

1. Local-first；Career Core 是 canonical truth。
2. Evidence != Fact != Signal != Decision != Outcome。
3. AI output 默认不是正式事实；MatchAssessment 是 proposal，不 mutate 任何事实。
4. SuggestedPriority 不能覆盖 UserPriority。
5. Official Capability Graph 与 Personal Capability Overlay 分离。
6. Project presence 不等于 personal mastery。
7. Coding Agent output 不能直接成为 Resume Fact。
8. Historical replay 必须使用 exact frozen references。
9. Dangling provenance 必须 fail loud。
10. Match 持久化不得写 Career Facts / Personal Capability State / priorities / ontology /
    Resume material。

## Contract 不够用时

不要私自修改 shared contract。输出 `CONTRACT CHANGE REQUEST` 并说明：Current Contract /
Problem / Proposed Change / Affected Modules / Migration Impact / Backward Compatibility。

## Implementation Rules

优先 `reuse > incremental refactor > small new abstraction > rewrite`。禁止 Scope Creep。
与任务无关的问题记录为 `FOLLOW-UP`。

参考实现要点（来自主 Agent 的既有代码摸底，写代码前仍需亲自核对）：

- `CommandService.commit()`（services/command_service.py）在单事务内写
  idempotency/entity_state/entity_revision/domain_event/transactional_write；
  `TransactionalWrite` protocol 要求 `idempotency_payload()` 与 `stage(session, *,
  entity_revision, occurred_at)`。
- immutable trigger 风格见 0008 `_create_immutable_triggers`。
- `EvidenceRepository.get()` 缺失返回 None、malformed 数据 raise RuntimeError。
- 命名风格：表 snake_case 单数、索引 `ix_`、约束 `ck_`、触发器 `trg_`。
- 通用 revision 用既有 `entity_state`/`entity_revision` 表（entity_kind 自定义，如
  `match_assessment`）。

## Testing

使用仓库虚拟环境（worktree 内运行，python/ruff 用主仓库 venv 绝对路径）：

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest tests/unit/test_match_persistence.py -q   # focused
& $python -m pytest -q                                        # full
& $ruff check backend tests migrations
& $ruff format --check backend tests migrations
git diff --check
```

必须覆盖：fresh DB upgrade 到 head；`0008 -> 0009 -> 0008 -> 0009` rehearsal；
immutable trigger 直接测试；atomic rollback；idempotent replay（同 idempotency_key 返回首次
结果）；dangling/不一致输入 fail loud；`get_revision` exact read。不要虚构测试结果。

## Commit

完成后：1) review diff；2) 删除 debug/temporary code；3) 跑 tests；4) explicit stage
（禁止 `git add .`）；5) commit 到 `kimi/v14-match-persistence`。建议 commit message：
`feat: add durable match gap persistence`。不要 merge 到 integration 或 main。

## Definition of Done

只有以下全部满足才能写 DONE：真实实现完成；核心行为有测试；上述测试全部通过（3 个已知
Windows symlink skip 除外）；没有 scope creep；没有偷偷修改 shared contract；没有破坏
canonical data；migration 0008->0009->0008->0009 兼容；commit 已创建。

## Final Report

输出：

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

现在开始：inspect → implement → test → review diff → commit → report。
