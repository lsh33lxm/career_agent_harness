# SUBAGENT PROMPT — incremental-rescan

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\incremental-rescan
```

## Branch

```text
kimi/v14-incremental-rescan
```

## Base Commit

```text
{worktree 创建时的 integration HEAD；git log --oneline -1 确认}
```

## Workstream

```text
P1：增量 Project Rescan（契约 0.10.0 + D-020）
```

## Task

实现增量项目重扫：

1. 先 inspect 现状：`services/project_scanner.py`（anchored readers，全文扫描）、
   `db/project_repository.py`（manifest/evidence reads）、migration 0004
   （project_scan_scope / project_source_manifest / project_evidence 表结构与 triggers）、
   `core/project/models.py`（ProjectSourceManifest/ProjectEvidence/Freshness）。
2. 新增 rescan 服务方法（位置按现状惯例，可并入 project service 层或新文件）：
   - `rescan_project(command, *, project_id, scan_scope_id, scope_revision)`：
     加载 exact scope revision → anchored scan → 与该项目上一版 manifest 逐 entry 比对
     （path → sha256/byte_length）→ 产出新 `ProjectSourceManifest` revision + 可审计 diff
     记录（added/changed/removed paths）。新 manifest 仍 pin exact scope revision。
   - diff 是记录不是静默 mutation：不自动改任何 ProjectEvidence。
   - `mark_stale_evidence(command, *, evidence_ids, manifest_revision, reason)`（或并入
     rescan 命令，按实现简洁性选择）：把指定的 accepted Project Evidence 的 freshness 显式
     置为 STALE，typed event（如 `project_evidence.marked_stale`）+ 单事务原子写；
     evidence 内容字段永不被改写；只允许 CURRENT → STALE 转换，其他转换 fail loud。
   - 全部经 `CommandService.commit` 原子写（typed rows + generic revision + event +
     idempotency）。
3. 安全不变量原样复用 anchored readers：deny-wins、no-follow、containment、平台守卫。
   rescan 不得引入新的文件系统访问路径绕过既有守卫。
4. 测试：
   - rescan diff 正确性（added/changed/removed；无变化时 diff 为空）；
   - 新 manifest pin exact scope revision；幂等重放；
   - mark_stale：成功路径 + 非 CURRENT 转换 fail loud + 不存在 evidence fail loud +
     回滚断言；accepted evidence 内容字段不变断言；
   - scope 安全回归（deny/reparse/越界路径仍被拒——复用或参照
     `tests/integration/test_project_scanner.py` 的既有用例，3 个 Windows symlink skip
     是已知限制，不要尝试绕过）。
5. 如 schema 不足（例如 diff 需要落表）：先尝试用既有表（manifest revision + JSON diff 记录
   是否够用需要评估 0004 结构）；确实不够就停下来发 CONTRACT CHANGE REQUEST，禁止私自加
   migration。

## Why This Task Exists

契约 0.10.0（`docs/v1.4/contracts.md` "Incremental project rescan" 节）+ D-020 已冻结。
Handoff 记录 Project Evidence 为 PARTIAL（"Safe full scan; no incremental/rescan
orchestration"）。本任务补上 enhancement loop 的 rescan 环节。

## Required Reading

```text
docs/v1.4/contracts.md            # 0.10.0 Incremental project rescan 节
docs/v1.4/decision-log.md         # D-008, D-011, D-020
backend/career_harness/services/project_scanner.py
backend/career_harness/db/project_repository.py
backend/career_harness/core/project/models.py
migrations/versions/0004_project_evidence.py
backend/career_harness/services/command_service.py
tests/integration/test_project_scanner.py
```

## Owned Paths

```text
backend/career_harness/services/project_scan_service.py（或按现状惯例的文件名）  # 新建
tests/ 下新增 rescan 相关测试                                                   # 新建
```

追加式修改（只追加、不改既有行为）：

```text
backend/career_harness/services/project_scanner.py   # 仅当需要暴露既有 reader 给新服务
```

## Read-only Paths

```text
backend/career_harness/core/
backend/career_harness/db/（repository 只读使用；缺 read 发 CONTRACT CHANGE REQUEST）
migrations/
apps/
docs/
```

## Forbidden Paths

```text
migrations/versions/        # 不写新 migration
apps/
importers/、D:\...\agent_rader
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.10.0`：diff 是记录不是 mutation；freshness 变化只走显式
命令；accepted evidence 内容永不改写；scanner 安全不变量不变。

## Product Invariants

1. Local-first；Career Core 是 canonical truth。
2. Evidence != Fact；rescan 产出的是记录/信号，不是 Fact。
3. Dangling provenance fail loud。
4. 不自动 promote 任何 evidence/capability。

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

explicit stage（禁止 `git add .`）→ commit 到 `kimi/v14-incremental-rescan`。建议 message：
`feat: add incremental project rescan`。不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；核心行为有测试且全部通过；无 scope creep；未改 shared contract；未加
migration；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出。

现在开始：inspect → implement → test → review diff → commit → report。
