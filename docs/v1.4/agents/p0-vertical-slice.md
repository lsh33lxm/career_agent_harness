# SUBAGENT PROMPT — p0-vertical-slice

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\p0-vertical-slice
```

## Branch

```text
kimi/v14-p0-vertical-slice
```

## Base Commit

```text
{创建时 integration HEAD，worktree 内 git log --oneline -1 确认}
```

## Workstream

```text
NEXT READY #2：P0 垂直链路端到端集成验证（测试-only workstream）
```

## Task

新增一个连贯的集成测试 fixture，用真实 service + disposable SQLite DB（0001→0012 全
migration）走通 P0 主链路，并断言每一步的 canonical 状态：

```text
Job/Requirement（propose → USER review → accepted）
→ Opportunity（admission，user-gated）
→ Match/Gap（MatchService.assess：resolve → policy → persisted assessment + canonical gaps）
→ Resume（base → agent propose patch → USER review accept → immutable ResumeRevision）
→ Application（prepare → USER 确认 submit）
→ Outcome（记录）
→ MatchService.replay（对落库的 assessment 做 stored-manifest replay，验证无 drift）
```

要求：

1. 一个（或少数几个）连贯 fixture 数据集贯穿全链路，断言相邻环节的 exact refs 一致
   （Opportunity 的 JobRef、Match manifest 的 requirement refs、ResumePatch 的
   fact/requirement refs、Application 的 resume_revision_id 等）。
2. 断言关键不变量：AI 提议不自动成为事实；prepared != submitted；replay 无 drift；
   UserPriority 不被任何步骤改写。
3. 只新增测试文件（和必要的 tests/support helper），不改任何实现代码。如果链路在现有
   service API 下走不通，不要改实现去迁就——把断点记录为 BLOCKED/FOLLOW-UP 并说明缺口。
4. 参照既有集成测试的 seed/构造模式：`tests/integration/test_match_service.py`、
   `test_fact_service.py`、`test_project_enhancement_service.py`、Application/Outcome 的
   既有测试（自行定位）。

## Why This Task Exists

Handoff（`docs/v1.4/HANDOFF_CODEX_TO_KIMI_2026-09-20.md` §I）指出：各组件 slice 全绿，
但没有一个端到端测试证明 P0 主链路。本任务补上这个 stage-acceptance 证据。

## Required Reading

```text
docs/v1.4/HANDOFF_CODEX_TO_KIMI_2026-09-20.md   # §I vertical slice 表
docs/v1.4/contracts.md                          # 0.8.0 全文
docs/v1.4/integration-log.md
tests/integration/                              # 既有集成测试模式
backend/career_harness/services/                # 各域 service 接口
```

## Owned Paths

```text
tests/integration/test_p0_vertical_slice.py    # 新建
tests/support/                                 # 可追加 helper（只追加）
```

## Read-only Paths

```text
backend/                                       # 全部只读
migrations/
docs/
```

## Forbidden Paths

```text
apps/
importers/、D:\...\agent_rader
backend/（任何实现代码；发现缺口就报告，不要修）
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.8.0` 全部不变量。

## Implementation Rules

测试-only。禁止 Scope Creep。链路断点记录为 `FOLLOW-UP` 并在 Final Report 里明确。

## Testing

```powershell
$python = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\python.exe'
$ruff = 'D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness\.venv\Scripts\ruff.exe'

& $python -m pytest tests/integration/test_p0_vertical_slice.py -q
& $python -m pytest -q
& $ruff check tests
& $ruff format --check tests
git diff --check
```

不要虚构测试结果。3 个已知 Windows symlink skip 不阻塞。

## Commit

explicit stage（禁止 `git add .`）→ commit 到 `kimi/v14-p0-vertical-slice`。建议 message：
`test: prove the p0 vertical slice end to end`。不要 merge 到 integration 或 main。

## Definition of Done

端到端测试真实通过（或链路断点被明确记录为 BLOCKED 并附证据）；全量 pytest 不回归；
无实现代码改动；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出。

现在开始：inspect → implement → test → review diff → commit → report。
