# SUBAGENT PROMPT — fact-promotion

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\fact-promotion
```

## Branch

```text
kimi/v14-fact-promotion
```

## Base Commit

```text
f933b8b feat: add claim and fact entity kinds
```

## Workstream

```text
W2-FACT（ExtractedClaim review + Fact promotion 持久化）
```

## Task

实现 ExtractedClaim / Fact 的 canonical 持久化与 promotion 路径：

1. 新建 additive migration `migrations/versions/0010_fact_promotion.py`
   （`down_revision = "0009_match_gap_persistence"`）：
   - `extracted_claim_identity`（claim_id PK）+ `extracted_claim_revision`
     （(claim_id, revision) 复合 PK）：claim_type、subject（entity_id + entity_kind）、
     proposed_value（bounded JSON）、evidence_ref_ids（子表或 bounded JSON，对齐既有风格）、
     extractor、extractor_version、confidence、status
     （proposed/accepted/rejected/superseded CHECK）、review 元数据（reviewed_by /
     reviewed_by_kind / review_reason / reviewed_at，proposed 时必须为 NULL——参照 0008
     requirement 的 review CHECK）、actor 元数据。identity 稳定 trigger + immutable
     revision trigger，风格对齐 0008。
   - `fact_identity`（fact_id PK，记录 candidate 归属若适用）+ `fact_revision`
     （(fact_id, revision) 复合 PK）：subject、fact_type、value（bounded JSON）、authority
     （user_asserted/document_supported/rule_verified CHECK）、source_claim_id +
     source_claim_revision（FK 到 extract_claim_revision）、evidence_ref_ids（子表或
     bounded JSON）、verified_at/verified_by。immutable triggers。
   - upgrade/downgrade 对称；disposable DB 验证 `0009 -> 0010 -> 0009 -> 0010`。
2. `backend/career_harness/db/models.py` 只追加对应 ORM rows（不改既有 rows）。
3. 新建 `backend/career_harness/db/fact_repository.py` typed reads：
   `get_claim(claim_id, revision=None)`、`get_fact(fact_id, revision=None)`、
   `list_facts_for_subject(entity_id)`（稳定排序）。缺失返回 None，malformed fail loud。
4. 新建 `backend/career_harness/db/fact_writes.py`：`ExtractedClaimWrite`（proposal，
   revision 1）、`ClaimReviewWrite`（追加 review revision）、`FactPromotionWrite`
   （fact revision 1；后续修正追加 revision）。stage 校验：
   - claim proposal：每个 evidence_ref_id 必须能通过 `evidence_ref` 表解析（fail loud）；
   - review：claim 存在、是 proposed 状态、reviewer 是 USER 或 RULE actor，且 reviewer
     不能是原 proposer（AI 不能自审）；
   - promotion：source claim 的 exact revision 存在且 status=accepted；authority 非 AI；
     每个 evidence_ref_id 解析；promotion 不得凭空造 claim。
5. 新建 `backend/career_harness/services/fact_service.py`：
   `propose_claim` / `review_claim` / `promote_fact`，全部经 `CommandService.commit`
   原子写（typed rows + generic revision + event + idempotency）。事件：
   `claim.proposed`、`claim.reviewed`、`fact.promoted`，payload 只含 metadata。
   `EntityKind.EXTRACTED_CLAIM` / `EntityKind.FACT` 已存在。
   review/promotion 不得 mutate Evidence、Capability、Match、Resume 任何表（测试断言）。
6. 测试（tests/unit + tests/integration 按现有惯例）：
   - fresh upgrade 到 head；`0009 -> 0010 -> 0009 -> 0010` rehearsal；immutable/identity
     trigger 直接测试；
   - propose/review/promote 成功路径；AI 自审被拒；非 accepted claim 不能 promote；
     dangling evidence ref fail loud；幂等重放；原子回滚（多表行数不变）；
   - typed reads exact/latest + malformed fail loud。

## Why This Task Exists

Resume patch 契约要求 `fact_refs` 可解析到 qualified Fact，而 `Fact`/`ExtractedClaim`
目前只有 core 模型（`core/evidence/models.py`），没有持久化；core 的
`promote_claim_to_fact` 是故意 raise 的占位。契约 0.5.0（`docs/v1.4/contracts.md` 的
"Claim review and Fact promotion"节）与 D-015 已冻结语义。本任务是 W2-RESUME 的前置。

## Required Reading

```text
docs/v1.4/contracts.md                 # 0.5.0 Claim review and Fact promotion + Evidence authority
docs/v1.4/decision-log.md              # D-015
docs/v1.4/migration-plan.md            # M3f
backend/career_harness/core/evidence/models.py   # ExtractedClaim / Fact / FactAuthority
migrations/versions/0008_job_requirement_persistence.py  # proposal/review 表与 trigger 风格
migrations/versions/0009_match_gap_persistence.py        # 最新 migration 风格
backend/career_harness/db/job_writes.py                  # proposal/review write 模式
backend/career_harness/services/job_service.py           # review 编排（USER-gated）参照
backend/career_harness/db/evidence_repository.py         # evidence_ref 表结构
backend/career_harness/services/command_service.py
tests/integration/test_match_service.py                  # 测试/seed 模式参照
```

## Owned Paths

```text
migrations/versions/0010_fact_promotion.py        # 新建
backend/career_harness/db/fact_repository.py      # 新建
backend/career_harness/db/fact_writes.py          # 新建
backend/career_harness/services/fact_service.py   # 新建
tests/ 下新增 fact 相关测试                        # 新建
```

追加式修改（只追加、不改既有逻辑）：

```text
backend/career_harness/db/models.py               # 只追加 ORM rows
```

## Read-only Paths

```text
backend/career_harness/core/        # EntityKind 已由 Lead 加好；core 模型只读
backend/career_harness/db/ 其他 repository/writes
migrations/versions/0001..0009
docs/
```

## Forbidden Paths

```text
apps/
importers/、D:\...\agent_rader
migrations/versions/0001..0009
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.5.0`。注意：`ExtractedClaim` 现有 core 模型字段
（claim_type/subject/proposed_value/evidence_refs/extractor/confidence/status）是既有契约
载体，不要重设计；如发现字段不足以满足 0.5.0，发 CONTRACT CHANGE REQUEST。

## Product Invariants

1. Local-first；Career Core 是 canonical truth。
2. Evidence != Fact != Signal != Decision != Outcome。
3. AI output 默认不是正式事实；AI 不能自审、不能自 promote。
4. SuggestedPriority 不能覆盖 UserPriority。
5. Official Capability Graph 与 Personal Capability Overlay 分离。
6. Dangling provenance 必须 fail loud。
7. review/promotion 不得 mutate Evidence / Capability / Match / Resume 表。

## Contract 不够用时

输出 `CONTRACT CHANGE REQUEST`，不要私自另起模型。

## Implementation Rules

`reuse > incremental refactor > small new abstraction > rewrite`。禁止 Scope Creep。无关问题
记录为 `FOLLOW-UP`。

## Testing

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest <你的 focused 测试> -q
& $python -m pytest -q
& $ruff check backend tests migrations
& $ruff format --check backend tests migrations
git diff --check
```

不要虚构测试结果。3 个已知 Windows symlink skip 不阻塞。

## Commit

review diff → 删除 debug code → 跑 tests → explicit stage（禁止 `git add .`）→ commit 到
`kimi/v14-fact-promotion`。建议 message：`feat: add claim review and fact promotion`。
不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；核心行为有测试且全部通过；migration rehearsal 通过；无 scope creep；未改
shared contract；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出。

现在开始：inspect → implement → test → review diff → commit → report。
