# SUBAGENT PROMPT — match-resolver

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

> 注意：本 workstream 依赖 match-persistence 先合入 integration。开始前确认 base commit
> 已包含 migration 0009、`MatchRepository`、`MatchAssessmentWrite`、`MatchService
> .record_assessment()` 与 `OpportunityRepository.get_revision()`。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\match-resolver
```

## Branch

```text
kimi/v14-match-resolver
```

## Base Commit

```text
13481e4 之后的 integration HEAD（即 match-persistence merge b04d08e + 文档 commit；worktree
创建时以 `git log --oneline -1` 确认为准）
```

## Workstream

```text
W2-MATCH-PERSIST（resolver/replay 半区）
```

## Task

实现 exact input resolver + assess 编排 + replay：

1. 新增 `backend/career_harness/services/match_resolver.py`（或按 service 层惯例命名）：
   - `MatchInputResolver.resolve(*, opportunity_id, opportunity_revision, candidate_id,
     requirements: tuple[(requirement_id, revision), ...]) -> MatchPolicyInput`
   - 全部走 exact reads：
     - Opportunity：`OpportunityRepository.get_revision(opportunity_id, revision)`；
     - Job：`JobRepository.get_job(job_id, revision)`（revision 来自 Opportunity JobRef）；
     - Requirements：`JobRepository.get_requirement(requirement_id, revision)` 逐条精确取，
       顺序保持 caller 输入顺序；禁止用 `list_requirements_for_job()` 推导；
     - Official nodes：按 requirement 的 `(capability_id, graph_version_id)` 精确读
       Capability repository；
     - Personal states：按 `(candidate_id, capability_id)` 解析当前 exact
       `(personal_state_id, revision)` 后，用 `get_personal_state(personal_state_id,
       revision)` 精确读；
     - Evidence bindings：`list_evidence_bindings(personal_state_id,
       personal_state_revision)`；
     - 每个 generic `evidence_ref_id` 必须逐个 `EvidenceRepository.get()`，返回 None 即
       fail loud；
     - Project Evidence：按 binding 的 `(project_evidence_id, project_evidence_revision)`
       精确读；
     - Project Capability States：按 capability 取 exact
       `(capability_state_id, revision)` 读。
   - 任何缺失 / dangling / 身份漂移一律 raise（fail loud），禁止静默跳过或降级。
2. `MatchService.assess(...)` 编排：resolve → `assess_match`（pure policy）→
   `record_assessment(...)`（match-persistence 已提供的原子写入）。Assessment 是 proposal，
   不得 mutate 任何 Career Fact / Personal Capability State / priority / ontology /
   Resume material。
3. `MatchService.replay(assessment_id)`：
   - 从 `MatchRepository.get_assessment()` 读 stored manifest 与 stored results；
   - 用 stored manifest 中的 exact refs 重新 resolve（与第 1 步共享 exact-read 路径，但输入
     完全来自 manifest，包括 ordered requirement refs、personal state revisions、binding
     refs、project state revisions）；
   - 用 stored `policy_version` 重跑 pure policy；policy_version 不是当前代码支持的版本时
     fail loud；
   - 比较完整 business output（每 requirement 的 classification、covered/missing scopes、
     reasons）与 stored results；任何 drift / missing ref fail loud；
   - replay 永远不写。
4. 测试：resolver 对每个输入源的 exact-read 与 dangling fail loud；assess 端到端（内存
   DB）；replay 成功路径与 drift 检测（例如底层 evidence 被替换/缺失、policy 输出被篡改
   的 stored row）。

## Why This Task Exists

Contract `0.4.0` 冻结了 resolver/replay 语义：历史 Match 必须能基于 frozen manifest 重放，
不能通过 latest-at-read API 伪装历史输入；`capability_evidence_binding.evidence_ref_id`
早于 migration 0007、没有 DB FK，resolver 必须逐个 resolve 并 fail loud。match-persistence
半区提供 durable schema 与原子写入，本半区完成"从 canonical store 到 frozen input"的桥。

## Required Reading

```text
docs/v1.4/contracts.md            # 0.4.0 Match persistence / resolver / replay 节
docs/v1.4/decision-log.md         # D-012, D-013, D-014
backend/career_harness/core/match_gap/        # pure policy
backend/career_harness/services/match_service.py   # persistence 半区产出
backend/career_harness/db/match_repository.py      # persistence 半区产出
backend/career_harness/db/job_repository.py
backend/career_harness/db/capability_repository.py
backend/career_harness/db/project_repository.py
backend/career_harness/db/evidence_repository.py
backend/career_harness/db/opportunity_repository.py
```

## Owned Paths

```text
backend/career_harness/services/match_resolver.py   # 新建
backend/career_harness/services/match_service.py    # 追加 assess/replay 编排
tests/unit/test_match_resolver.py                   # 新建（或按现有惯例拆分）
```

## Read-only Paths

```text
backend/career_harness/core/
backend/career_harness/db/            # repository 只读使用；缺 read 就发 CONTRACT CHANGE REQUEST
migrations/
docs/
```

## Forbidden Paths

```text
apps/
importers/、D:\...\agent_rader
migrations/versions/                   # 不加 migration；缺 schema 能力就停下来报告
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.4.0`：exact reads only；dangling fail loud；replay 用
stored manifest + stored policy_version；禁止 latest-at-read 冒充历史输入。

## Product Invariants

同 match-persistence prompt 的 10 条（Local-first … dangling provenance fail loud）。

## Contract 不够用时

输出 `CONTRACT CHANGE REQUEST`（Current Contract / Problem / Proposed Change /
Affected Modules / Migration Impact / Backward Compatibility），不要私自另起模型。

## Implementation Rules

`reuse > incremental refactor > small new abstraction > rewrite`。禁止 Scope Creep。无关问题
记录为 `FOLLOW-UP`。

## Testing

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest tests/unit/test_match_resolver.py -q
& $python -m pytest -q
& $ruff check backend tests migrations
& $ruff format --check backend tests migrations
git diff --check
```

不要虚构测试结果。3 个已知 Windows symlink skip 不阻塞。

## Commit

review diff → 删除 debug code → 跑 tests → explicit stage（禁止 `git add .`）→ commit 到
`kimi/v14-match-resolver`。建议 message：`feat: add match input resolver and replay`。
不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；resolver/assess/replay 核心行为有测试且全部通过；无 scope creep；未改 shared
contract；未动 canonical data；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出（Workstream/Status/Branch/Commit/Changed Files/
Implemented/Tests Run/Test Results/Migration Impact/Contract Changes/Known Limitations/
Follow-up Tasks/Integration Notes）。

现在开始：inspect → implement → test → review diff → commit → report。
