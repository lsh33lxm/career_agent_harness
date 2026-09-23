# SUBAGENT PROMPT — capability-inbox-review

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\capability-inbox-review
```

## Branch

```text
kimi/v14-capability-inbox-review
```

## Base Commit

```text
f268e85 docs: freeze capability inbox review contract 0.9.0
```

## Workstream

```text
P1：Capability Inbox review service（候选能力节点审核 → 正式 ontology）
```

## Task

实现 CandidateCapabilityNode 的 review/promote 写路径：

1. 先 inspect 现状：`backend/career_harness/db/capability_repository.py`（candidate inbox 读）、
   `db/models.py`（candidate 相关 rows）、migration 0003（candidate 表结构）、
   `core/capability/models.py`（CandidateCapabilityNode + CandidateCapabilityStatus）。
   弄清候选节点的写路径目前是否存在（propose service 是否已有）。
2. 新建 `backend/career_harness/services/capability_review_service.py`（或并入既有
   capability service 文件，按现状惯例）：
   - `review_candidate(command, *, candidate_node_id, decision, reason, merge_target= None)`：
     decision ∈ accept/reject。accept 必须 USER actor；reject 允许 USER 或 RULE；
     reviewer ≠ discoverer（discovered_by）。经 `CommandService.commit` 原子写，事件
     `capability_candidate.reviewed`（payload 纯 metadata）。
   - accept 且非 merge：在同一事务内发布新 `CapabilityGraphVersion`（parent = 当前 released
     版本），新节点加入新版本；遵守 D-007 的发布顺序（子行先、graph version 行最后，
     deferred FK + seal triggers）。不改动任何已 release 的版本。
   - accept 且 merge：记录 `merge_target_capability_id` 指向既有 canonical identity，目标
     identity 必须存在（fail loud），不创建新节点。
   - 若现状缺少候选节点的 proposal 写路径，补一个最小的 `propose_candidate`
     （agent/rule/user 均可提议，status=pending，source evidence refs 必须可解析 fail
     loud）；若已存在则复用。
3. 测试：propose/review 成功路径；AI 自审拒绝；非 USER accept 拒绝；merge 目标不存在
   fail loud；dangling evidence ref fail loud；幂等重放；原子回滚；已 release graph
   version 不可变断言；accept 后新版本可读且旧版本不变。
4. 如需要新表/新列（例如 candidate 的 review 持久化字段在 0003 已存在则复用；不够就发
   CONTRACT CHANGE REQUEST 而不是私自加 migration——先检查 0003 schema 是否已足够）。

## Why This Task Exists

契约 0.9.0 + D-019 已冻结 inbox review 语义。Handoff §J：Capability Inbox 有存储和读，
缺 review service。这是 Capability 切片从 PARTIAL 走向可用的关键一步。

## Required Reading

```text
docs/v1.4/contracts.md            # 0.9.0 Capability inbox review 节 + Capability graph 节
docs/v1.4/decision-log.md         # D-007, D-019
backend/career_harness/core/capability/models.py
backend/career_harness/db/capability_repository.py
backend/career_harness/db/models.py（capability 相关 rows）
migrations/versions/0003_capability_core.py
backend/career_harness/services/fact_service.py   # USER-gated review 模式参照
tests/integration/test_fact_service.py            # 测试模式参照
```

## Owned Paths

```text
backend/career_harness/services/capability_review_service.py   # 新建（或按现状并入既有 service）
backend/career_harness/db/capability_writes.py                 # 新建（如需要）
tests/ 下新增 capability review 测试                            # 新建
```

追加式修改（只追加、不改既有逻辑）：

```text
backend/career_harness/db/models.py      # 仅当确有新 row 需要（先发 CONTRACT CHANGE REQUEST）
```

## Read-only Paths

```text
backend/career_harness/core/
migrations/versions/
backend/career_harness/db/ 既有 repository
apps/
docs/
```

## Forbidden Paths

```text
migrations/versions/        # 不写新 migration；schema 不够就发 CONTRACT CHANGE REQUEST
apps/
importers/、D:\...\agent_rader
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.9.0`：USER-only accept、不自审、release 不可变、merge
语义、reviewed candidates 不可变历史。official graph 与 personal overlay 保持分离。

## Product Invariants

1. Local-first；Career Core 是 canonical truth。
2. AI 可以发现，不能随意定义；AI 不能自审。
3. Official Capability Graph 与 Personal Capability Overlay 分离。
4. Dangling provenance fail loud。
5. Review 不得 mutate personal overlay / bindings / Match / priorities。

## Contract 不够用时

输出 `CONTRACT CHANGE REQUEST`，不要私自另起模型或加 migration。

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

explicit stage（禁止 `git add .`）→ commit 到 `kimi/v14-capability-inbox-review`。建议
message：`feat: add capability inbox review flow`。不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；核心行为有测试且全部通过；无 scope creep；未改 shared contract；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出。

现在开始：inspect → implement → test → review diff → commit → report。
