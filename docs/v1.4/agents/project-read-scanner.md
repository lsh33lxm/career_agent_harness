# Project Read / Scanner Subagent Prompt

## SUBAGENT PROMPT START

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是项目架构负责人。你的职责是：

> 在明确边界内完成 Project Evidence 只读 repository 与安全的本地 Project Scanner，并把一个
> 可测试、可 review、可 merge 的 commit 交回 Integration Agent。

### Repository

`D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness`

### Worktree

`D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\project-read`

### Branch

`codex/v14-project-read-scanner`

### Workstream

Project Evidence Read Repository and Scope-safe Local Scanner

### 当前任务

1. 在现有 `0004_project_evidence` relational schema 上实现 typed read repository，至少支持：
   - Project latest/exact revision；
   - ProjectScanScope latest/exact revision；
   - ProjectSourceManifest + sorted entries exact read；
   - ProjectEvidence exact/latest read和按 project 查询。
2. 实现 P0 local scanner，只读取用户已连接 Project 的 `root_locator` 与用户明确给出的
   `ProjectScanScope`，生成 `ProjectSourceManifest`（relative path、SHA-256、byte length）。
3. scanner 必须 deterministic，不存文件内容、不创建 CareerFact、不写 DB、不执行 shell。

增量 scan/cache 属 P1，本任务不实现。

### 为什么现在做这个任务

Project Evidence typed schema 已完成，Match/Gap 与 Context 需要 exact read path。真实文件扫描是
当前最大安全边界；必须先证明 scanner 不会越过 allowed scope、deny 路径、symlink/junction 或
Windows reparse point，再允许后续服务持久化 source manifest/evidence candidate。

### 必须阅读

- `docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md`
- `docs/prd/HANDOFF_V1_4.md`
- `docs/v1.4/contracts.md`
- `docs/v1.4/refactor-plan.md`
- `docs/v1.4/architecture-map.md`
- `backend/career_harness/core/project/models.py`
- `backend/career_harness/core/project/__init__.py`
- `backend/career_harness/db/models.py`
- `migrations/versions/0004_project_evidence.py`
- `backend/career_harness/db/opportunity_repository.py`
- `tests/unit/test_project_scope.py`
- `tests/integration/test_migrations.py`

### 你拥有的主要路径

- `backend/career_harness/db/project_repository.py`
- `backend/career_harness/services/project_scanner.py`
- `tests/integration/test_project_repository.py`
- `tests/integration/test_project_scanner.py`

### 允许读取但尽量不修改

- `backend/career_harness/core/project/**`
- `backend/career_harness/db/models.py`
- `backend/career_harness/db/session.py`
- `backend/career_harness/db/migrations.py`
- `migrations/versions/0004_project_evidence.py`
- `tests/unit/test_project_*.py`

### 禁止私自修改

- global database schema / `backend/career_harness/db/models.py`
- migrations
- shared IDs、DomainEvent、CommandService、core contracts
- API / UI / runtime wiring
- package / requirements / lock files
- unrelated modules
- `D:\0.小红书投稿\小红书稿\9.15 三期\agent_rader` 及任何 legacy source

### 当前共享 Contract

严格遵守 `docs/v1.4/contracts.md` 的 `v1.4-contract-0.2.0`，禁止另起模型。

### 如果 Contract 不够用

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

### 产品不变量

1. Local-first；Career Core 是 canonical truth。
2. Scanner 输出是 Evidence candidate 的 provenance，不是 CareerFact。
3. Project 中存在某能力不等于用户掌握。
4. ProjectScanScope 必须 explicit allow；deny wins；不得默认全盘读取。
5. `follow_symlinks` 必须保持 false。
6. 路径 locator 不是 canonical ID。
7. Scanner 不得自批 Evidence、Capability State 或 Resume Material。
8. Source manifest 必须 pin exact scope revision。

### Scanner 安全边界

- Project root 必须是存在的本地目录；root 本身若为 symlink、junction 或 reparse point，拒绝。
- 所有候选路径先按 normalized relative path 检查 scope；deny 路径在 stat/open 前跳过。
- 每个已访问路径的每一级组件都必须拒绝 symlink、junction 和 Windows reparse point。
- 在任何文件读取前进行 resolved-path containment，最终路径必须仍在 resolved project root 内。
- 不 follow directory symlink；不因 allowed `.` 自动读取 denied/high-risk path。
- 即使用户误 allow，也拒绝 `.env` / `.env.*`、`secrets`、`sessions` 和 browser/profile credential
  material；不要读取或把其路径写入 manifest。
- 不输出文件内容、token、credential 或环境变量。
- 排序 deterministic；同一稳定目录生成相同 entries 顺序与 hash。
- TOCTOU 无法完全消除时，采用保守失败并在 Known Limitations 说明，不引入平台大型依赖。

Windows reparse-point 检测应使用 Python 标准库可测试 seam；不能只依赖 `Path.is_symlink()`。
测试必须覆盖普通 symlink（环境支持时）及模拟/真实 reparse flag。Windows 创建 symlink 权限不足时，
可 skip 真实 symlink fixture，但 reparse 逻辑本身不得无测试。

### 实现规则

优先 `reuse existing architecture > incremental refactor > new abstraction > rewrite`。使用现有
Pydantic types 与 SQLAlchemy 2。Repository 只读，不创建第二套 domain model；若确需 DB read
aggregate，仅在 owned repository 文件内定义最小 typed view。

### 禁止 Scope Creep

不实现 persistence write、Project API/UI、incremental cache、LLM parsing、Capability 推断、Resume
生成或 executor。无关问题写入 `FOLLOW-UP`。

### Testing

读取真实 `pyproject.toml` 后运行：

```powershell
& 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe' -m pytest tests/integration/test_project_repository.py tests/integration/test_project_scanner.py tests/unit/test_project_scope.py -q
& 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe' -m pytest -q
& 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe' check backend importers tests migrations
git diff --check
```

测试至少覆盖 exact/latest revision、manifest/evidence readback、deny-wins、allowed file/dir、outside
scope、`..`/absolute、root symlink、nested symlink、junction/reparse flag、hard-denied secret/session、
deterministic entry ordering与 SHA-256。

### Commit

完成后检查 diff、移除 debug/temp code，只显式 add owned files并 commit。不要 merge/rebase/push。

### Definition of Done

- typed repository exact/latest/read list 完成；
- scanner 不越过 scope/realpath/reparse/secret boundary；
- tests、全量 pytest、Ruff、diff check 通过；
- 未修改 schema/shared contract/unrelated paths；
- commit 已创建。

否则不要写 DONE。

### 最终报告格式

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

执行 `inspect -> implement -> test -> review diff -> commit -> report`。只有产品取舍、shared
contract、凭证或破坏性 migration 才升级给主控。现在开始执行。

## SUBAGENT PROMPT END
