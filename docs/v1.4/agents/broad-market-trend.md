# SUBAGENT PROMPT — broad-market-trend

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\broad-market-trend
```

## Branch

```text
kimi/v14-broad-market-trend
```

## Base Commit

```text
{worktree 创建时的 integration HEAD；git log --oneline -1 确认}
```

## Workstream

```text
P1：Broad Market Trend 派生 read model（契约 0.12.0 + D-022）
```

## Task

实现 Broad Market Trend 派生读模型（纯读，无写路径、无 migration）：

1. 先 inspect：`core/capability/models.py`（MarketBinding / MarketBindingScope）、
   `db/capability_repository.py`（market binding 读接口）、`core/today/`（read model 模式
   参照）、`services/today_service.py`。
2. 新建 trend 读模型（位置建议 `core/market/models.py` 或并入 capability 模块，按现状惯例）：
   按 capability 聚合 broad-scope MarketBinding：count、exact binding refs、输入 revision 集；
   同输入确定性输出；空输入空结果。
3. 新建 `services/market_trend_service.py`（纯读）：从 capability repository 读 broad
   bindings 并聚合。零写入（测试断言所有写表行数不变）。
4. 测试：聚合正确性、确定性（乱序输入等价）、空输入、target-scope binding 不混入 broad
   聚合、binding revision 集记录。

## Why This Task Exists

契约 0.12.0 + D-022 已冻结：Broad Market Trend 是派生 read model，用于趋势/探索/校验，
永不驱动投资决策、永不改优先级或个人能力状态。

## Required Reading

```text
docs/v1.4/contracts.md            # 0.12.0 Broad market trend 节
docs/v1.4/decision-log.md         # D-022
backend/career_harness/core/capability/models.py
backend/career_harness/db/capability_repository.py
backend/career_harness/core/today/（read model 模式参照）
backend/career_harness/services/today_service.py
```

## Owned Paths

```text
backend/career_harness/core/market/ 或按现状选择的新模块文件   # 新建
backend/career_harness/services/market_trend_service.py        # 新建
tests/ 下新增 trend 测试                                        # 新建
```

## Read-only Paths

```text
backend/career_harness/ 既有全部
migrations/
apps/
docs/
```

## Forbidden Paths

```text
migrations/versions/    # 无新 migration
apps/
importers/、D:\...\agent_rader
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.12.0`：派生 read model；on-read 计算；确定性；记录输入
revision 集；永不写、永不重排 target 输入、永不 mutate 任何 canonical 状态。

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
& $ruff format --check backend tests
git diff --check
```

不要虚构测试结果。3 个已知 Windows symlink skip 不阻塞。

## Commit

explicit stage（禁止 `git add .`）→ commit 到 `kimi/v14-broad-market-trend`。建议 message：
`feat: add broad market trend read model`。不要 merge 到 integration 或 main。

## Definition of Done

真实实现完成；核心行为有测试且全部通过；零写入；确定性；无 scope creep；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出。

现在开始：inspect → implement → test → review diff → commit → report。
