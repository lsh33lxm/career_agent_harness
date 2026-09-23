# SUBAGENT PROMPT — resume-core

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\resume-core
```

## Branch

```text
kimi/v14-resume-core
```

## Base Commit

```text
24aa5bf feat: add resume patch and revision entity kinds
```

## Workstream

```text
W2-RESUME（Resume Base/Patch/Revision 核心域 + 持久化）
```

## Task

实现 Resume 垂直切片的核心（不含 render、不含 UI）：

1. 新建 `backend/career_harness/core/resume/models.py`（core 域模型，FrozenModel 风格对齐
   既有 core 模块；更新 `core/resume/__init__.py` 导出）：
   - `ResumeBase`：resume_id、candidate_id、revision、schema_version、sections（bounded
     JSON 结构化内容， FrozenModel 子模型或受限 dict）、created/updated 元数据。
   - `ResumePatchOperation`：operation（set/insert/remove）、target_path、
     expected_value_hash、proposed_value、fact_refs（exact (fact_id, revision)）、
     evidence_refs、requirement_refs（exact (requirement_id, revision)）、reason。
   - `ResumePatch`：patch_id、resume_id、base_revision、operations（min_length=1）、
     generator_run_id（可选）、status（proposed/accepted/rejected）、review 元数据
     （proposed 时必须为空，review 后必填，模式对齐 JobRequirement）。
   - `ResumeRevision`：revision_id、resume_id、base_revision、ordered accepted patch refs
     （exact (patch_id, patch_revision)）、content（应用后的结构化内容）、
     content_sha256、created 元数据。immutable。
2. 新建 additive migration `migrations/versions/0011_resume_core.py`
   （`down_revision = "0010_fact_promotion"`）：resume_identity/resume_revision?——按既有
   identity+revision 风格设计表：resume_base（identity + revision 表或单表+generic
   revision，对齐既有模式）、resume_patch（identity + revision，含 operations bounded
   JSON + review CHECK）、resume_revision（immutable，content hash，FK 到 exact base
   revision 与 patch revisions）。immutable/identity/review triggers 对齐 0008/0010 风格。
   upgrade/downgrade 对称，disposable DB 验证 `0010 -> 0011 -> 0010 -> 0011`。
3. `backend/career_harness/db/models.py` 只追加 ORM rows。
4. 新建 `backend/career_harness/db/resume_repository.py` typed reads：exact/latest base
   revision、patch exact/latest、revision by id；malformed fail loud。
5. 新建 `backend/career_harness/db/resume_writes.py` +
   `backend/career_harness/services/resume_service.py`：
   - `save_base_revision`（USER actor 强制）：新 resume 或追加 base revision。
   - `propose_patch`（user 或 agent）：写路径校验目标 base revision 存在；每个 fact_ref
     解析到 canonical Fact 且 authority 非 AI（用 FactRepository）；每个 evidence_ref 经
     `EvidenceRepository.get()` 解析；dangling/unqualified fail loud。
   - `review_patch`（USER-only，且 reviewer ≠ proposer）：accepted/rejected 追加 review
     revision。
   - `create_revision`（USER-only）：从 exact base revision + 调用方给定的 ordered accepted
     patch refs 生成 immutable ResumeRevision：重新校验每个 patch 确实 accepted 且属于同一
     base revision；应用 operations（校验 expected_value_hash 与当前内容匹配，不匹配 fail
     loud）；计算 content_sha256。
   - 全部经 `CommandService.commit` 原子写；事件 `resume_base.saved`（或类似过去时命名）、
     `resume_patch.proposed`、`resume_patch.reviewed`、`resume_revision.created`，payload
     只含 metadata。EntityKind.RESUME / RESUME_PATCH / RESUME_REVISION 已存在。
   - 任何 resume 写不得 mutate Fact/Evidence/Capability/Match 表（测试断言行数不变）。
6. 测试（tests/unit + tests/integration 按惯例）：
   - migration rehearsal + trigger 直测；
   - base/patch/review/revision 成功路径；agent propose + user accept 全流程；
   - AI 自审拒绝；非 accepted patch 不能进入 revision；expected_value_hash 不匹配 fail
     loud；dangling fact/evidence ref fail loud；unqualified（AI authority）fact 拒绝；
   - 幂等重放、原子回滚（多表行数不变）。

## Why This Task Exists

纵向闭环的 Resume 环：契约 0.6.0 + D-016 已冻结
（`docs/v1.4/contracts.md` "Resume write path" 节）。ResumeBase/Patch/Revision 目前零代码；
Fact（`d43ebe4`）与 Enhancement（`cadba69`）已合入，patch 的 fact_refs 现在可以真实解析。

## Required Reading

```text
docs/v1.4/contracts.md              # 0.6.0 Resume write path + Resume truth
docs/v1.4/decision-log.md           # D-015, D-016
docs/v1.4/migration-plan.md         # M3g
AGENT_CAREER_HARNESS_PRD_v1.2.md    # §17 Resume Workbench（patch 字段语义）
backend/career_harness/core/evidence/models.py   # Fact / FactAuthority
backend/career_harness/core/job/                 # proposal/review 模型模式
backend/career_harness/db/fact_repository.py     # get_fact 签名
backend/career_harness/db/fact_writes.py         # 写路径模式
backend/career_harness/services/fact_service.py  # USER-gated review 模式
backend/career_harness/db/evidence_repository.py
migrations/versions/0010_fact_promotion.py       # 最新 migration 风格
tests/integration/test_fact_service.py           # 测试/seed 模式参照
```

## Owned Paths

```text
backend/career_harness/core/resume/models.py        # 新建
backend/career_harness/core/resume/__init__.py      # 更新导出
migrations/versions/0011_resume_core.py             # 新建
backend/career_harness/db/resume_repository.py      # 新建
backend/career_harness/db/resume_writes.py          # 新建
backend/career_harness/services/resume_service.py   # 新建
tests/ 下新增 resume 测试                            # 新建
```

追加式修改（只追加、不改既有逻辑）：

```text
backend/career_harness/db/models.py   # 只追加 ORM rows
```

## Read-only Paths

```text
backend/career_harness/core/（resume/ 以外）
backend/career_harness/db/ 其他 repository/writes
backend/career_harness/services/ 其他 service
migrations/versions/0001..0010
docs/
```

## Forbidden Paths

```text
apps/
importers/、D:\...\agent_rader
migrations/versions/0001..0010
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.6.0`。`Resume`（`core/lifecycle.py`）是既有实体壳，
不要重设计；如需调整 core 既有模型，发 CONTRACT CHANGE REQUEST。

## Product Invariants

1. Local-first；Career Core 是 canonical truth。
2. Evidence != Fact != Signal != Decision != Outcome。
3. AI-inferred material 不得进入 accepted patch；AI 不能自审。
4. SuggestedPriority 不能覆盖 UserPriority。
5. Dangling provenance 必须 fail loud。
6. Resume 写不得 mutate Fact / Evidence / Capability / Match / priority 表。
7. ResumeRender 是 projection，本 workstream 不实现 render。

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
& $ruff format --check backend tests migrations
git diff --check
```

不要虚构测试结果。3 个已知 Windows symlink skip 不阻塞。

## Commit

review diff → 删除 debug code → 跑 tests → explicit stage（禁止 `git add .`）→ commit 到
`kimi/v14-resume-core`。建议 message：`feat: add resume base patch and revision core`。
不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；核心行为有测试且全部通过；migration rehearsal 通过；无 scope creep；未改
shared contract；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出。

现在开始：inspect → implement → test → review diff → commit → report。
