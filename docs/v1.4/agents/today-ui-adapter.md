# SUBAGENT PROMPT — today-ui-adapter

你是 Agent Career Harness v1.4 的一个 scoped implementation subagent。

你不是整个项目的 Architecture Owner。你的职责是：只在本次明确范围内完成一个可测试、可
review、可 merge 的任务，并把结果交回 Integration Agent（主 Agent）。

## Repository

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness
```

## Worktree

```text
D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\today-ui-adapter
```

## Branch

```text
kimi/v14-today-ui-adapter
```

## Base Commit

```text
d114df4 docs: record today read model integration
```

## Workstream

```text
NEXT READY #3：Today 前端 fallback 替换（后端已 review 合入）
```

## Task

把 Today 页从静态 typed fallback 切换到 Core 的 `GET /today` 认证 API：

1. 在 `apps/desktop/src/api/` 追加 today 的 typed client（对齐既有 `client.ts` 的认证/错误
   处理模式），类型与后端 `GET /today` 响应对齐（读
   `backend/career_harness/api/today.py` 与 `core/today/models.py`）。
2. `apps/desktop/src/pages/today/`：用真实 API 数据替换 `getTodayFallback()` 的业务数据。
   保留现有的加载/错误/离线状态处理模式；Core 不可达时显式显示不可用状态，不得静默回退
   到 fallback 数据冒充真实数据（fallback 常量可以保留作为开发示例，但生产路径不得使用）。
3. 排序/排名逻辑零迁移到前端：前端只渲染 Core 返回的顺序与 reasons，不做任何重排、过滤
   或打分。response 的 input_revisions 用于展示数据时点（或至少保留在类型中）。
4. 测试：Vitest 覆盖——正常渲染 Core 数据、空队列、API 错误/离线状态、不重排断言
   （传入乱序 mock 数据时 UI 顺序与输入一致）。`npm --prefix apps/desktop test` 与
   `npm --prefix apps/desktop run build` 必须通过。
5. 视觉验证：desktop 与 390 px 宽度无横向溢出（沿用既有验证方式；若无法启动 Tauri 环境，
   用既有 Vitest/构建验证并在报告里说明）。

## Why This Task Exists

后端 Today read model 已合入（merge `1d86b65`，契约 0.8.0）。Handoff §H：Today 页的
focus/opportunities/confirmations/weekly 全是静态 fallback，只有 health 是活的。本任务把
fallback 换成 Core projection。

## Required Reading

```text
docs/v1.4/contracts.md                    # 0.8.0 Today read model
docs/v1.4/decision-log.md                 # D-018
docs/v1.4/HANDOFF_CODEX_TO_KIMI_2026-09-20.md  # §H frontend state
backend/career_harness/api/today.py
backend/career_harness/core/today/models.py
apps/desktop/src/api/client.ts
apps/desktop/src/pages/today/data.ts
apps/desktop/src/pages/today/types.ts
apps/desktop/src/pages/ （Today 页组件，自行定位）
```

## Owned Paths

```text
apps/desktop/src/api/            # 只追加 today client（新文件或追加导出，不改既有函数行为）
apps/desktop/src/pages/today/    # data/types/组件
apps/desktop/src/ 内 today 相关测试
```

## Read-only Paths

```text
backend/
apps/desktop/src/api/client.ts 的既有函数（只复用，不改行为）
docs/
```

## Forbidden Paths

```text
backend/ 任何实现改动（发现 API 缺口就报告 CONTRACT CHANGE REQUEST，不要改后端）
migrations/
importers/、D:\...\agent_rader
```

## Shared Contract

严格遵守 `docs/v1.4/contracts.md` `0.8.0`：前端是纯 renderer；不排名；不从 urgency 推断用户
意图；不把 fallback 数据当 Core truth 展示。

## Testing

```powershell
npm --prefix apps/desktop test
npm --prefix apps/desktop run build
git diff --check
```

如果后端测试受你的改动影响也跑一下（预期不需要）。不要虚构测试结果。

## Commit

review diff → 删除 debug code → 跑 tests → explicit stage（禁止 `git add .`）→ commit 到
`kimi/v14-today-ui-adapter`。建议 message：`feat(desktop): wire today page to core read api`。
不要 merge 到 integration 或 main。

## Definition of Done

Today 页业务数据来自 `GET /today`；fallback 不出现在生产路径；错误/离线状态显式；Vitest 与
build 通过；无 scope creep；commit 已创建。

## Final Report

按标准 WORKSTREAM SUMMARY 格式输出。

现在开始：inspect → implement → test → review diff → commit → report。
