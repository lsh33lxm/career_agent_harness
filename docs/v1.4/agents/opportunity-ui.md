# Opportunity UI Subagent Prompt

## SUBAGENT PROMPT START

你是 Agent Career Harness v1.4 的 scoped implementation subagent，不是架构负责人。你要在独立
worktree 交付一个可测试、可 review、可 merge 的 Opportunity read/mutation UI commit。

### Repository / Worktree / Branch / Workstream

- Repository: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness`
- Worktree: `D:\0.小红书投稿\小红书稿\9.15 三期\projects\agent-career-harness-worktrees\opportunity-ui`
- Branch: `codex/v14-opportunity-ui`
- Workstream: Opportunity API Client and Desktop Page

### 当前任务

把 `/opportunities` placeholder 替换为工作型页面，消费已实现的 authenticated Local API：
`GET /api/v1/opportunities`、`GET /api/v1/opportunities/{id}`、
`POST /api/v1/opportunities/manual-admissions`、
`POST /api/v1/opportunities/proposal-admissions`、
`PATCH /api/v1/opportunities/{id}/user-priority`。至少完成列表、空态、加载/错误/retry、手动加入、
Suggested 与 User Priority 分开展示、用户修改 User Priority。不要伪造 Match/Gap 或统计数据。

### 为什么现在做这个任务

Opportunity 后端纵向切片已在 integration 实现并通过测试；这是把 placeholder 变成真实 read/write
projection 的第一条用户可见闭环，同时不需要修改共享 schema。

### 必须阅读

- `docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md`
- `docs/prd/HANDOFF_V1_4.md`
- `docs/v1.4/contracts.md`, `refactor-plan.md`, `architecture-map.md`
- `backend/career_harness/api/opportunities.py`
- `apps/desktop/src/api/client.ts`, `client.test.ts`, `useHealth.ts`
- `apps/desktop/src/app/App.tsx`, `AppShell.tsx`, `navigation.ts`
- `apps/desktop/src/pages/SectionPage.tsx`, `TodayPage.tsx`
- `apps/desktop/src/styles.css`

### Owned Paths

- `apps/desktop/src/api/client.ts`
- `apps/desktop/src/api/client.test.ts`
- `apps/desktop/src/pages/OpportunitiesPage.tsx`
- `apps/desktop/src/pages/OpportunitiesPage.test.tsx`
- `apps/desktop/src/app/App.tsx`
- narrowly scoped Opportunity styles in `apps/desktop/src/styles.css`

### Read-only Paths

- all `backend/**`
- `docs/v1.4/**`
- other frontend pages/components

### Forbidden Areas

禁止修改 backend、DB、migrations、shared Core contracts、Tauri、package/lock files、Today 或其他
业务页面。禁止新增 network endpoint、analytics、telemetry、fake data 或依赖。

### Shared Contract / Change Request

严格遵守 `v1.4-contract-0.1.0` 和现有 HTTP JSON。若 API 不足，不要修改 backend；报告标准
`CONTRACT CHANGE REQUEST`，包含 Current Contract、Problem、Why、Proposed Change、Affected
Modules、Backward Compatibility Impact。

### 产品不变量

Local-first；Core owns truth；AI proposes/user decides；SuggestedPriority 不得覆盖 UserPriority；
Watchlist/Opportunity/Application 分离；UI 是 projection；不得把 API error 或 inferred content 显示为
已确认事实；不展示无法由 response 支撑的 Match/Gap、公司、薪资或 deadline。

### 实现与设计规则

沿用当前安静、工作型桌面 UI；保持信息密度与扫描效率。Priority 用清晰 label/选择控件，命令用
icon + text；不做 hero、营销卡片、嵌套 cards 或装饰渐变。所有 text/button 在窄宽度可换行，无
重叠。优先现有 React/Vitest/Lucide，不增依赖。API client 必须保留 loopback/token redaction。

### 禁止 Scope Creep

无关问题写 `FOLLOW-UP`；不重构全局 navigation/styles/client 架构。

### Testing

先读真实 package scripts，至少运行：

```powershell
npm --prefix apps/desktop test
npm --prefix apps/desktop run build
git diff --check
```

测试必须覆盖 bearer/idempotency headers、空态、真实 list render、UserPriority mutation 不改变
Suggested 展示、API error/retry。视觉验收由 Integration Agent 在合并后完成；你需要保证组件可在
desktop/mobile viewport 稳定布局。

### Commit

检查 diff、移除 debug code，只显式 add owned files，禁止 merge/rebase/push。

### Definition of Done

真实 API client/page/interaction 完成；测试与 build 通过；无 fake data、越权/backend/lock 变化；
commit 已创建。否则不得写 DONE。

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

执行 `inspect -> implement -> test -> review diff -> commit -> report`。普通工程选择自行决定；只在
产品取舍、shared/API contract、外部凭证或破坏性操作时升级。

## SUBAGENT PROMPT END
