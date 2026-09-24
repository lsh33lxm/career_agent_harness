# Agent Career Harness — Product & Implementation PRD v1.2

> **文档角色：** 总产品定义 + 产品信息架构 + 桌面端架构 + Career Core 架构契约 + 迁移与实施基线  
> **版本：** v1.2 Integrated Desktop Baseline  
> **日期：** 2026-09-17  
> **状态：** Proposed Integrated Baseline；用户确认后取代 v1.1 成为主 PRD  
> **产品名称：** Agent Career Harness  
> **首要用户：** 项目拥有者本人，personal-first / single-user-first  
> **主要产品形态：** Local-first Desktop Career Workspace  
> **默认技术形态：** Tauri 2 + React/TypeScript/Vite + Python Local API Sidecar + SQLite + Local Artifact Store  
> **辅助工作面：** Feishu Companion Workspace  
> **核心原则：** Local-first / Evidence-constrained / Human-in-the-loop / Replayable / Replaceable-but-not-plugin-owned

---

# 0. 文档定位、来源与优先级

## 0.1 本文档是什么

本文件是 Agent Career Harness 当前的**总 PRD**。它同时定义：

- 产品是什么、用户如何使用；
- Desktop / Core / Worker / Feishu 的边界；
- Evidence / Fact / Signal / Decision / Outcome 的语义；
- Canonical Data Contract；
- Resume、Application、Interview、Radar 等核心模块；
- 当前 Agent Radar 资产如何迁移；
- Project Cards 与 Product Reference Cards 如何约束后续 AI 开发；
- P0A/P0F/P0B/P0C/P0D/P1/P2/P3 的实施顺序；
- ADR、Gate、验收和 Definition of Done。

本文档整合：
1. Agent Career Harness PRD v1.0 / v1.1；
2. 38 张 GitHub Project Cards 架构复核；
3. Project Cards Architecture Review；
4. 12 个已有 ADR Candidates；
5. `CURRENT_REPO_STRUCTURE.md`；
6. Agent Radar 原 PRD / handoff / Deep Research；
7. 飞书 Phase 10A / 10B；
8. Desktop-first 产品决策；
9. 求职方舟 AI、JobPal、Magic Resume 等产品参考。

## 0.2 与 v1.1 的关系

v1.1 的工程核心继续保留：

```text
ExtractedClaim / FactProposal
current state + immutable revision + DomainEvent
transactional outbox
LocalStepRunner
typed Adapter Ports
Playwright deterministic browser substrate
Docling primary + fallback routing
Resume Content / Patch / Revision / Render
Opportunity / Application / Submitted separation
Feishu Inbox / Outbox / expected_revision / conflict / DeadLetter
SQLite + content-addressed Artifact Store
P0A / P0B / P0C staged migration
```

v1.2 的核心变化：

```text
Optional Local Review Console
            ↓
Primary Desktop Application

Feishu Human Workspace
            ↓
Feishu Companion Workspace
```

并新增：

```text
Discover
Watchlist
Quick Capture
Opportunity Dossier
Application Answer Bank
JD-tailored Resume Workbench
Interview Calendar
Career Funnel Insights
```

## 0.3 当前事实冲突处理

旧状态文档曾记录主工作簿 46 个工作表；最新 `CURRENT_REPO_STRUCTURE.md` 的物理检查发现当前根目录主工作簿为 61 个工作表。

因此：

- 当前物理仓库状态以 `CURRENT_REPO_STRUCTURE.md` 为准；
- 历史业务样本数与审核状态仍以已确认项目状态文档为准；
- 不把不同时间点数值静默合并；
- 正式发布必须重新生成唯一 Snapshot。

## 0.4 冲突优先级

```text
1. 本 PRD 的 Hard Constraints
2. Approved ADR
3. Core Schema / Security / Permission Contract
4. 本 PRD 的模块 Acceptance Criteria
5. Project Cards Architecture Review
6. Project Cards / Product Reference Cards
7. Deep Research / Historical PRD
8. 外部项目设计
9. Coding Agent 自主判断
```

---

# 1. Executive Summary

Agent Career Harness 是一个**本地优先、证据约束、人工保留最终控制权的个人求职 Agent 运行环境和桌面工作台**。

核心闭环：

```text
市场变化
  ↓
Evidence
  ↓
Fact / Signal
  ↓
Discover
  ↓
Opportunity
  ↓
Match / Gap
  ↓
Resume
  ↓
Application Prepare
  ↓
Human Submit
  ↓
Interview
  ↓
Outcome
  ↓
下一轮 Decision
```

产品必须让用户在关键时刻回答：

```text
这条信息从哪里来？
它是 Fact 还是 Signal？
这次推荐基于哪个 Snapshot？
为什么这个岗位值得考虑？
哪些 Candidate Facts 真正匹配？
AI 改简历时引用了哪些真实事实？
这次申请用了哪版 Resume？
哪一步由 Agent 做、哪一步由用户批准？
最终发生了什么？
哪些 Outcome 正在影响下一轮计划？
```

---

# 2. Product Definition

## 2.1 一句话定义

> **Agent Career Harness：一个 local-first、evidence-constrained 的个人求职 Agent 运行环境，通过持续市场观察、可信事实、可审阅自动化和真实 Outcome，把“发现机会—准备—投递—面试—复盘”变成一个可回放的个人职业闭环。**

## 2.2 North Star

系统持续维护一个：

```text
可信
可回查
可行动
可修正
可复盘
```

的个人职业上下文。

Agent 负责：

```text
observe
extract
classify
compare
propose
prepare
render
remind
```

用户保留：

```text
fact confirmation
important decisions
expression
relationship building
interview performance
legal / identity answers
final submission
```

## 2.3 核心长期资产

```text
Evidence
Candidate Facts
Career History
Approvals
Audit
Outcomes
```

模型、浏览器、飞书、renderer、workflow runtime、parser 都必须可替换。

---

# 3. Non-Goals

当前不建设：

- 通用招聘 SaaS；
- 企业 ATS；
- 职位聚合网站；
- 通用 Agent Framework；
- 公共插件市场；
- 公共求职社区；
- 无人值守海投机器人；
- CAPTCHA / Cloudflare / stealth / proxy 绕过工具；
- 自动法律、身份、work authorization、demographic 承诺；
- 单纯简历生成器；
- 单纯 AI 聊天机器人；
- 题库镜像站；
- 多 Agent 角色扮演聊天室；
- 完整 Event Sourcing 平台；
- 同时运行多套 Workflow Runtime；
- 同时默认运行多套 Document Parser；
- 向量记忆作为履历事实库；
- Feishu 作为 canonical database。

特别说明：

> “不建设完整 Magic Resume 式 SaaS”不等于“不建设前后端分离桌面产品”。

本项目要建设的是 Agent Career Harness 自己的 local-first Desktop Application。

---

# 4. Current Project Reality

## 4.1 当前真实工作区

当前 `agent_rader` 不是 conventional application repo，而是：

```text
历史 Agent Radar 数据研究工作区
+
多阶段 Python / PowerShell 流水线
+
Excel Research Workspace
+
多数据根
+
Snapshots / Evidence / Delivery Artifacts
+
Feishu TEST / STAGING 测试资产
+
PRD / Prompt / Handoff
```

当前没有确认存在：

```text
HTTP backend
frontend project
database
migration layer
dependency lockfile
unified app launcher
agent runtime
production Feishu connector
```

## 4.2 历史区域

```text
work/
  legacy collection / clean / review / workbook

codex/data/
  stronger data-first raw / normalized / derived / snapshot

data/
  publication tables / candidates / snapshot copies

evidence/
  archived originals

references/
  historical workbooks / packages

agent_radar_test_workspace/
  Feishu/Lark TEST tooling

交付/
  release artifacts
```

## 4.3 最大结构问题

当前没有 repo-level authority manifest 明确：

```text
work/clean
vs
data/
vs
codex/data/
vs
Excel
vs
Feishu
```

谁是真相。

因此禁止直接把某一历史目录认定为新 Core Truth。

必须：

```text
Inventory
→ Compare
→ Reconcile
→ Approved Import Manifest
→ Core Import
```

## 4.4 当前未完成项

- `N=137` 主候选逐条确认；
- 7 条跨包疑似重复；
- 220 条日期/公司/岗位问题；
- 105 条题目映射问题；
- 34 条图片 Seed 多模态 + 人工验收；
- 唯一正式 Snapshot；
- 同一 Snapshot 下 Radar / Personal Plan / Evidence 展示；
- Career Core importer / reconciliation / cutover；
- 可靠 Feishu Projection / Command sync。

## 4.5 Feishu 现实

已有本地测试 helper、payload builder、response artifacts、A/B/C 结构和 TEST/STAGING 文档；但不能据此宣称 PROD connector、durable sync、远程实时状态或生产权限已完成。

---

# 5. Target Product Shape

```text
┌──────────────────────────────────────────────────┐
│           Agent Career Harness Desktop            │
│         Tauri + React / TypeScript / Vite         │
│                                                  │
│ Today / Discover / Opportunities / Resume        │
│ Applications / Interviews / Prep / Insights      │
│ Evidence / Settings / Capture                    │
└──────────────────────┬───────────────────────────┘
                       │ Local API
                       ▼
┌──────────────────────────────────────────────────┐
│             Python Career Harness Backend         │
│ Career Core / Commands / Policies / Revisions    │
│ Evidence / Snapshot / Audit / Outcome            │
│ LocalStepRunner / Sync / API                     │
└───────────────┬──────────────────┬───────────────┘
                │                  │
                ▼                  ▼
       SQLite Canonical DB     Artifact Store
                │
                ▼
┌──────────────────────────────────────────────────┐
│                 Local Workers                    │
│ Source Watchers / Parser / Model / RenderCV      │
│ Playwright Browser Worker / Feishu Adapter       │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
             Feishu Companion Workspace
         Push / Wiki / Review / Mobile Glance
```

---

# 6. Surface Ownership

## 6.1 Desktop

Primary Product Surface。

负责：

```text
Discover
Watchlist
Opportunity
Evidence
Candidate Profile
Resume Workbench
Application Prepare
Interviews
Prep
Insights
Settings
Quick Capture
```

Desktop 通过 Local API 发 typed Command，不直接写 SQLite。

## 6.2 Local Career Core

唯一 canonical business surface。

负责 IDs、entities、revisions、commands、policies、approvals、facts、evidence、application truth、outcome、audit、snapshot、migration、sync metadata。

## 6.3 Local Workers

负责高成本/外部副作用任务：

```text
source observation
parsing
OCR
model tasks
resume rendering
browser automation
Feishu sync
scheduled checks
```

Worker 不拥有 truth。

## 6.4 Feishu Companion

负责：

```text
Morning/Weekly Brief
Radar summary
Opportunity summary
Review Queue
Weekly Plan
notifications
Wiki
mobile glance
```

不负责完整 Resume、browser session、credential 或任何实体唯一存储。

---

# 7. Hard Constraints

## HC-01
Canonical Core 在本地。

## HC-02
Desktop 是 Primary Product Surface，但不是 Truth Store。

## HC-03
Feishu 是 Companion，不是 canonical database。

## HC-04
Agent / Adapter 没有 Truth Ownership。

## HC-05
`Evidence / Fact / Signal / Decision / Outcome` 不可合并。

## HC-06
Parser / OCR / LLM 输出先进入 `ExtractedClaim / FactProposal`，不直接成为 Fact。

## HC-07
Browser 保持 Human-in-the-loop。

允许：

```text
navigate/read/extract/fill/upload/validate/save_draft/screenshot
```

禁止默认：

```text
CAPTCHA bypass
stealth
proxy evasion
mass apply
unknown legal answer
unattended final submit
```

## HC-08
不做 Big Bang Rewrite。

## HC-09
所有外部副作用必须幂等且可审计。

## HC-10
不确定性必须可见。

## HC-11
Workflow State 不等于 Business State。

## HC-12
Legacy Workspace 在 Cutover 前保持只读保护。

---

# 8. Primary User & Jobs To Be Done

P0-P2 首先服务项目拥有者本人。

用户希望：

1. 自定义目标公司、职位、方向、地点和来源；
2. 持续发现新岗位和市场变化；
3. 把 URL、截图、JD、PDF、招聘信息快速保存；
4. 区分事实和推断；
5. 对感兴趣岗位形成独立档案；
6. 分析 JD 与个人真实经历匹配；
7. 找出知识、Coding、项目表达 Gap；
8. 针对 JD 改简历但不编造事实；
9. 自动准备网申重复字段；
10. 跟踪投递、面试、Follow-up 和 Outcome；
11. 根据真实结果调整后续策略。

---

# 9. Desktop Information Architecture

```text
⌂ Today

⌕ Discover
  ├─ Jobs
  ├─ Companies
  ├─ Radar
  └─ Watchlist

◎ Opportunities

▤ Resume

↗ Applications

◷ Interviews

◇ Prep

▥ Insights

☷ Evidence

⚙ Settings
```

全局：

```text
+ Capture
⌘ Ask Harness / Command Palette
```

`Ask Harness` 是辅助 command surface，不是主 UI。

---

# 10. Today

回答：

```text
发生了什么？
什么跟我最相关？
今天该做什么？
什么需要我确认？
```

聚合：

- 新 Job / JobRevision；
- 新 Signal；
- Review Queue；
- Opportunity next action；
- Resume Patch；
- FollowUp；
- Interview approaching；
- Weekly Plan；
- blocked workflow；
- Feishu sync error。

Today 是 read model，不是 canonical domain。

---

# 11. Discover / Radar / Watchlist

## 11.1 Discover vs Opportunity

```text
Discover = 外部有哪些值得看的岗位
Opportunity = 我决定认真考虑的机会
```

## 11.2 Watchlist

支持：

```text
Companies
Roles
Locations
Topics
Keywords
Sources
```

Source 可为官方 careers、ATS、GitHub、Engineering Blog、RSS、Web Page、manual source。

## 11.3 Source Priority

```text
Official Careers / ATS
Official Company Source
Verified First-hand Evidence
Trusted Public Source
Discovery Aggregator
Unverified Social / User Capture
```

## 11.4 Radar Signal

必须显示：

```text
evidence
confidence
counter_evidence
generated_at
expiry/review status
```

---

# 12. Quick Capture

Input：

```text
URL
text
screenshot
image
PDF
JD
recruiter message
interview invitation
clipboard
```

Pipeline：

```text
CaptureItem
→ Artifact
→ Parser/OCR/LLM
→ ExtractedClaim
→ Human/Rule Review
→ Evidence / Job / Opportunity / Interview / Note
```

`CaptureItem` 是 intake object，不是 Fact。

---

# 13. Opportunity Dossier

Opportunity 是 Desktop 的中心工作对象。

页面：

```text
Overview
JD
Evidence
Match
Gap
Resume
Application
Interviews
FollowUps
Timeline
Outcome
```

状态：

```text
discovered
watching
qualified
preparing
declined
expired
archived
```

关系：

```text
Opportunity
├── Company
├── Job / JobRevision
├── Evidence
├── Signals
├── MatchAssessment
├── Gap
├── ResumeRevision
├── Application
├── InterviewSession[]
├── FollowUp[]
└── Outcome[]
```

---

# 14. Candidate Profile

Core：

```text
CandidateProfile
CandidateFact
CandidateFactRevision
CandidatePreference
Experience
ProjectExperience
SkillEvidence
AnswerFact
```

Fact authority：

```text
user_asserted
document_supported
rule_verified
```

模型判断不是 authority。

---

# 15. Evidence Authority Model

## Evidence

```text
Source
SourceSnapshot
Artifact
DocumentRevision
EvidenceRef
EvidenceSpan
ProvenanceEdge
```

## ExtractedClaim

```text
claim_id
claim_type
subject_ref
proposed_value
evidence_refs[]
extractor
extractor_version
confidence
status
review_reason
```

status：

```text
proposed
accepted
rejected
superseded
```

## Signal

必须有 evidence / counter-evidence / confidence / generator / expiry。

## Decision

记录 actor、reason、input snapshot/revisions、override。

## Outcome

记录 observed_at、source、evidence、recorded_by、supersession。

---

# 16. Match, Gap & Prep

MatchAssessment 基于冻结输入，不是 Candidate Fact。

Gap：

```text
knowledge
coding
project_expression
system_design
behavioral
```

Weekly Plan 默认 3–5 项。

Task：

```text
task_id
type
estimated_time
priority
reason
evidence_refs
snapshot_id
status
reflection
```

新 Signal 不默认打乱已确认当周计划。

---

# 17. Resume Workbench

核心流程：

```text
Candidate Facts
→ Resume Content
→ Opportunity + JobRevision
→ ResumePatchProposal
→ Desktop Diff Review
→ Accept/Edit/Reject
→ ResumeRevision
→ RenderManifest
→ RenderedArtifact
```

Core：

```text
Resume
ResumeRevision
ResumePatchProposal
RenderManifest
RenderedArtifact
```

Patch 最低字段：

```text
base_resume_revision_id
operation
target_path
expected_value_hash
proposed_value
fact_refs[]
job_requirement_refs[]
reason
generator_run_id
status
```

Desktop 至少表现为：

```text
JD Requirements | Current Resume | AI Suggestions
```

每条建议显示原文、建议、理由、Fact refs、JD refs、uncertainty 和 Accept/Edit/Reject。

RenderCV 只负责 deterministic render，不拥有 Resume truth。

---

# 18. Application Answer Bank

实体：

```text
AnswerFact
ApplicationAnswer
```

字段：

```text
canonical_key
question_pattern
value
source
revision
sensitivity
fill_policy
verified_at
last_used_at
```

fill policy：

```text
AUTO_FILL_SAFE
REVIEW_BEFORE_FILL
ALWAYS_ASK
```

例如：

```text
email → AUTO_FILL_SAFE
salary expectation → REVIEW_BEFORE_FILL
work authorization → ALWAYS_ASK
```

---

# 19. Applications

实体：

```text
Application
ApplicationEvent
ApplicationBlocker
FormPreparation
ApprovalRequest
FollowUp
Outcome
```

状态：

```text
preparing
ready_for_review
submitted_by_user
screen
oa
interview
offer
rejected
withdrawn
closed
```

不变量：

```text
Tracked Job != Application
Prepared != Submitted
Clicked button != verified Submitted
```

Submitted 仅接受用户确认或可验证 portal receipt。

---

# 20. Browser / Application Prepare

架构：

```text
Desktop
→ Local API
→ Browser Worker
→ Playwright
→ Real Browser Session
```

Tauri WebView 不承担 ATS automation。

STOP 条件：

```text
CAPTCHA
2FA
login wall
unknown identity field
legal commitment
work authorization
salary commitment
demographic question
```

处理：

```text
STOP
→ ApplicationBlocker
→ ask human
```

Stagehand 仅作为 opt-in recovery experiment，继承同一 allowlist 和 forbidden actions。

---

# 21. Interviews

必须区分：

```text
InterviewEvidenceEvent
= 外部市场面经证据

InterviewSession
= 用户自己的真实面试
```

InterviewSession：

```text
interview_session_id
application_id
company
role
round
scheduled_at
location_or_link
status
prep_plan_ref
notes
reflection
outcome_ref
```

面试后：

```text
Reflection
→ Gap
→ Decision
→ Next Weekly Plan
```

---

# 22. Insights

支持：

```text
Application → Screen → Interview → Offer
Time to next stage
Source funnel
Company funnel
ResumeRevision funnel
Blocker frequency
Follow-up effectiveness
Interview gap recurrence
```

任何解释显示样本量和 uncertainty。

---

# 23. Feishu Companion

Core → Feishu：

```text
Transactional Outbox
+
Idempotent Upsert
```

Projection 行：

```text
core_entity_id
entity_type
core_revision
environment
data_class
snapshot_id
run_id
sync_status
last_synced_at
```

Feishu → Core：

```text
Durable Cursor
+
CommandInbox
```

Command：

```text
actor
idempotency_key
expected_revision
source_record
payload_schema
```

冲突人工 review，不 last-write-wins。

---

# 24. Canonical Data Contract

所有 canonical entity：

- Core 生成 stable opaque ID；
- 有 schema version / created_at / created_by；
- 可变业务内容 immutable revision；
- command write 使用 expected_revision；
- 重要变化产生 DomainEvent；
- 默认 tombstone / supersession；
- Feishu ID、URL、Windows path 不作为 canonical ID。

Runtime / Sync：

```text
Command
IdempotencyRecord
DomainEvent
Run
RunManifest
StepRun
RunEvent
ModelRun
ToolCall
ApprovalRequest
ApprovalEvent
OutboxMessage
CommandInbox
DeadLetter
ProjectionRecord
SyncCursor
MigrationRun
MigrationReport
Mismatch
```

Canonical state + revision + DomainEvent + OutboxMessage 同事务提交。

---

# 25. Local Runtime

Run：

```text
queued
running
waiting_human
succeeded
failed
cancelled
```

StepRun：

```text
pending
running
blocked
succeeded
failed
skipped
```

P0-P2 使用 Harness-owned LocalStepRunner，不引入通用 durable workflow service。

Replay = 冻结输入后产生新 Run，不回写旧事件。

---

# 26. Model Layer

定义 `ModelTaskPort`。

ModelRun 统一记录：

```text
provider
model_id
parameters
prompt_version
schema_version
input_hash
output_hash
usage
latency
error
retry_count
```

P0/P1 直接 provider adapter；Pydantic AI 可评估为 typed model-call adapter。

P0 不部署 LiteLLM / Langfuse / multi-agent platform。

---

# 27. Document Pipeline

```text
structured source
→ deterministic parser
→ Docling
→ conditional Unstructured
→ per-page/region PaddleOCR
→ LLM semantic mapping
```

每次 parsing 生成 DocumentRevision，并记录 parser/version/config/input hash/span/quality/fallback reason。

Parser output 不自动成为 Fact。

---

# 28. Storage

Canonical：

```text
SQLite
```

Artifact：

```text
local content-addressed filesystem
artifact_id + sha256
```

Artifact class：

```text
public_source
personal
sensitive
credential_session
```

credential/session 不进入普通 Artifact Store。

---

# 29. Desktop Technical Architecture

默认：

```text
Desktop shell: Tauri 2
Frontend: React + TypeScript + Vite
Backend: Python local service
API: FastAPI/Pydantic preferred
Database: SQLite
Migration: Alembic preferred
Browser: Playwright
Renderer: RenderCV
Artifact: local filesystem + SHA-256
Feishu: Adapter
```

FastAPI / SQLAlchemy / Alembic 属于 implementation preference，可替换但不得改变 domain contract。

Tauri 负责：

```text
desktop lifecycle
window
sidecar lifecycle
native dialog
OS integration
updater
capability boundary
```

主要 Career business logic 保持在 Python。

开发：

```text
React/Vite
→ 127.0.0.1
→ Python API
```

发布：

```text
Tauri
→ Python sidecar
→ random localhost port
→ ephemeral launch token
→ React
```

禁止 bind `0.0.0.0`。

---

# 30. Desktop Security

必须：

```text
localhost only
per-launch token
strict CORS/origin
minimal Tauri capabilities
separate browser session store
OS Keychain/local secret store
log redaction
sidecar crash recovery
Core transaction independent of UI process
```

---

# 31. Repository Strategy

当前 `agent_rader/` 定义为：

> Legacy Agent Radar Research Workspace

不要直接原地大规模整理。

建立：

```text
agent-career-harness/
```

作为正式软件 repo，从第一天启用 Git、gitignore、lockfile、tests、ADR、migration。

禁止把 legacy workspace 直接 `git add .` 全量提交。

---

# 32. Target Repository Structure

```text
agent-career-harness/
├── README.md
├── pyproject.toml
├── package.json
├── .gitignore
├── .env.example
├── apps/
│   └── desktop/
│       ├── src/
│       │   ├── app/
│       │   ├── pages/
│       │   │   ├── today/
│       │   │   ├── discover/
│       │   │   ├── opportunities/
│       │   │   ├── resume/
│       │   │   ├── applications/
│       │   │   ├── interviews/
│       │   │   ├── prep/
│       │   │   ├── insights/
│       │   │   ├── evidence/
│       │   │   └── settings/
│       │   ├── features/
│       │   ├── components/
│       │   └── api/
│       └── src-tauri/
│           ├── src/
│           ├── capabilities/
│           └── tauri.conf.json
├── backend/
│   └── career_harness/
│       ├── api/
│       ├── core/
│       │   ├── candidate/
│       │   ├── evidence/
│       │   ├── market/
│       │   ├── opportunity/
│       │   ├── resume/
│       │   ├── application/
│       │   ├── interview/
│       │   ├── prep/
│       │   ├── outcome/
│       │   ├── approval/
│       │   ├── run/
│       │   └── snapshot/
│       ├── workflows/
│       ├── adapters/
│       │   ├── sources/
│       │   ├── documents/
│       │   ├── models/
│       │   ├── browser/
│       │   ├── resume/
│       │   └── feishu/
│       ├── workers/
│       ├── db/
│       └── services/
├── importers/
│   └── agent_radar/
├── schemas/
├── migrations/
├── research/
│   ├── deep_research/
│   ├── project_cards/
│   └── product_cards/
│       ├── qiuzhifangzhou.md
│       ├── jobpal.md
│       └── magic_resume_product.md
├── docs/
│   ├── prd/
│   ├── architecture/
│   ├── adr/
│   └── migration/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── fixtures/
└── scripts/
```

---

# 33. Legacy Migration

```text
Existing Agent Radar
→ read-only inventory
→ import candidate Core
→ identity map
→ reconciliation
→ dual-run comparison
→ approved cutover
→ legacy read-only observation
```

必须生成 `LEGACY_IMPORT_MANIFEST.json`：

```text
source_workspace
source_files
hashes
snapshot_sources
identity_mapping
approved_entities
excluded_entities
deferred_mismatches
importer_version
imported_at
```

只有 counts/member IDs/hash/provenance/mismatch/backup/restore 均通过后，才允许：

```text
SQLite = canonical truth
```

Cutover 后：

```text
Excel = research/export
Legacy files = historical source
Feishu = projection
```

---

# 34. Project Cards

38 张 Project Cards 的现有架构复核继续生效。

Direct Dependency candidates：

```text
Docling
Playwright
RenderCV
```

Service：

```text
changedetection.io
```

Adapter candidates：

```text
Stagehand
Pydantic AI
Unstructured
PaddleOCR
JobSpy
Mem0 (P3)
```

Design reference 包括 DeepSeek Harness、LangGraph、Magic Resume、JobHuntBot、Career-Ops、job-tracker、browser-use 等。

当前不作为 Harness runtime 的项目包括 CrewAI、AutoGen、OpenAI Agents SDK、Temporal、Prefect、Trigger.dev、Huginn、ApplyPilot、OfferPilot。

---

# 35. Product Reference Cards

目录：

```text
research/product_cards/
```

至少：

```text
qiuzhifangzhou.md
jobpal.md
magic_resume_product.md
```

记录：

```text
Product
Observed At
Target User
Core Journey
Information Architecture
Best UX Patterns
Automation Patterns
Data Model Hints
What We Borrow
What We Do Not Borrow
Mapped Harness Modules
PRD Delta Candidates
```

Project Card 回答“怎么实现”；Product Card 回答“用户怎么用”。

---

# 36. Functional Requirements

## Desktop
- DESK-001：Feishu 离线时 Desktop 独立启动。
- DESK-002：所有 mutation 通过 Local API / Command。
- DESK-003：Desktop crash 不损坏 Core transaction。
- DESK-004：支持 Global Capture。
- DESK-005：支持 Opportunity Dossier。
- DESK-006：支持 Evidence backlink。

## Discover
- DISC-001：支持 Company/Role/Location/Topic/Keyword Watch。
- DISC-002：支持 Source Registry。
- DISC-003：Discovery 不自动成为 verified Fact。
- DISC-004：支持加入 Opportunity。

## Capture
- CAP-001：URL/Text/Image/PDF。
- CAP-002：Artifact + ExtractedClaim。
- CAP-003：低置信度进入 Review。

## Resume
- RES-001：结构化 Content。
- RES-002：immutable Revision。
- RES-003：AI 只能 PatchProposal。
- RES-004：Patch 带 fact/job refs。
- RES-005：Accept/Edit 生成新 Revision。
- RES-006：Renderer 可替换。

## Application
- APP-001：Opportunity/Application 分离。
- APP-002：Answer Bank 支持 fill policy。
- APP-003：Playwright prepare-only。
- APP-004：高风险未知字段 Blocker。
- APP-005：Submitted 需用户确认/receipt。
- APP-006：记录实际 ResumeRevision。

## Interview
- INT-001：InterviewSession Calendar。
- INT-002：prep checklist。
- INT-003：reflection。
- INT-004：reflection 可形成 Gap，但不是自动 Fact。

## Insights
- INS-001：funnel。
- INS-002：resume revision breakdown。
- INS-003：source breakdown。
- INS-004：小样本 uncertainty。

## Feishu
- FEI-001：Outbox。
- FEI-002：CommandInbox。
- FEI-003：幂等。
- FEI-004：冲突 review。
- FEI-005：Projection 可重建。

---

# 37. Security & Privacy

Secret 不进入：

```text
Git
Feishu Base
Project Cards
Prompt
ordinary logs
public artifacts
```

优先 OS Keychain / local secret store / env injection。

PII 默认 least collection / least projection / least logging。

完整 Resume、Offer、Address 默认不进 Feishu。

Browser cookie/token/profile：

```text
separate storage
short lifecycle
no generic Artifact Store
no Model input
no Feishu
cleanup policy
```

P0B 必须 consistent backup + artifact manifest + hash verification + restore rehearsal。

---

# 38. Testing

## Unit
domain invariants、state transitions、command validation、claim promotion、patch conflict、fill policy。

## Integration
SQLite transaction、outbox、migration、parser、RenderCV、Playwright safety、Feishu STAGING。

## Contract
所有 Adapter 测 input/output/capability/side effect/error/idempotency。

## Safety
自动验证：

```text
TEST cannot enter PROD
Agent cannot approve own output
Signal cannot silently become Fact
Parser output is not Fact
Unknown legal field creates Blocker
Browser cannot autonomous final-submit
Feishu delete cannot delete Core
Feishu failure cannot corrupt Core
Same idempotency key cannot duplicate effects
Credential/session never enters ordinary Artifact Store
```

---

# 39. Success Metrics

不以抓取岗位数、自动投递数、Agent 数、插件数为主要指标。

优先：

```text
Evidence coverage
Review closure rate
Snapshot reproducibility
Qualified Opportunities
Weekly Plan completion
Resume Patch accept/edit/reject
Application preparation time
Application → Screen
Screen → Interview
Interview → Offer
ResumeRevision → Outcome traceability
Blocker recovery
Feishu sync conflict/dead-letter
Migration mismatch / rollback readiness
```

---

# 40. Implementation Phases

## P0A — Legacy Agent Radar Closure

Scope：

- 冻结影响正式 Snapshot 的继续补采；
- 收口 7/220/105；
- 34 图片 Seed + human review；
- 唯一 N；
- SnapshotManifest；
- Radar/Plan/Evidence 重建；
- 发布一致性检查。

Exit：

```text
unique published snapshot_id
TEST leakage = 0
Discovery in formal frequency = 0
unreviewed media in formal = 0
unconfirmed LeetCode ID in recommendation = 0
formal evidence backlink coverage = 100%
34 images have ModelRun + human result
all publication surfaces share snapshot_id
legacy files preserved
```

## P0F — New Application Foundation

与 P0A 并行。

Scope：

```text
new Git repo
Tauri + React shell
Python API health endpoint
SQLite empty schema bootstrap
app data directory
config/secret abstraction
test skeleton
```

不做 canonical cutover、真实 browser automation、Feishu PROD writes。

## P0B — Minimum Career Core & Migration

Gate：ADR-001/007/009/010 P0 范围。

Scope：

```text
SQLite schema
Artifact Store
importer
identity map
migration runner
Command/Revision/Claim/DomainEvent/Idempotency/StepRun
reconciliation
backup/restore
```

## P0C — Feishu Staging Companion

Gate：ADR-004/008 P0 范围。

实现 adapter、Outbox、CommandInbox、Projection、SyncCursor、DeadLetter、STAGING dry-run。

## P0D — Desktop Read-Only Product MVP

读取：

```text
Today
Radar
Discover
Opportunity
Evidence
```

允许少量低风险 Command。

## P1 — Personal Career Intelligence + Resume

```text
CandidateProfile/Fact
Watchlist/Monitoring
JobRevision/Signal
Opportunity/Match/Gap
WeeklyPlan
Quick Capture
Resume/Patch/Revision/Render
Answer Bank baseline
Document routing
```

Exit：

```text
real job change
→ Evidence
→ Opportunity
→ Gap
→ Resume Patch
→ Human Review
→ Rendered Resume
```

## P2 — Application / Browser / Interview / Outcome

```text
Playwright Worker
Portal Adapter
FormPreparation
Answer Bank
ApplicationBlocker
Human Submit
FollowUp
InterviewSession
Outcome
Insights
```

Exit：

```text
Opportunity
→ tailored Resume
→ prepared form
→ human review
→ human submit
→ Interview
→ Outcome
→ next Decision
```

## P3 — Platformization

只在 P0-P2 真实成立后评估：

```text
dynamic Plugin Registry
third-party extensions
external workflow runtime
Multi-Agent
Advanced Soft Memory
Langfuse/LiteLLM
distributed scheduler
limited collaboration
```

---

# 41. ADR Registry

现有：

```text
ADR-001 Canonical Storage and Transaction Boundary
ADR-002 Local Workflow Runtime
ADR-003 Browser Execution and AI Recovery
ADR-004 Feishu Projection/Command/Conflict/Outbox
ADR-005 Resume Content/Patch/Revision/Render
ADR-006 Document Parsing/OCR
ADR-007 Domain Event/Run Event/Replay
ADR-008 Adapter/Capability Boundary
ADR-009 Artifact/PII/Retention/Export/Delete
ADR-010 Agent Radar Migration/Cutover/Rollback
ADR-011 Model/Trace/Eval
ADR-012 Canonical Context vs Soft Memory
```

新增：

```text
ADR-013 Desktop Application Architecture
ADR-014 Frontend ↔ Local Backend Contract
ADR-015 Desktop / Feishu Product Surface Boundary
ADR-016 New Application Repo vs Legacy Workspace
```

推荐审批顺序：

```text
001 / 007 / 010 / 013 / 014 / 016
→
009 / 002 / 004 / 008 / 011 / 015
→
005 / 006
→
003
→
012
```

ADR-013 proposed：

```text
Tauri 2 + React/TypeScript/Vite + Python sidecar
```

ADR-014 proposed：

```text
127.0.0.1 + random port + ephemeral token + REST/JSON
```

ADR-015 proposed：

```text
Desktop = Primary Product Workspace
Feishu = Companion
Core = Truth
```

ADR-016 proposed：

```text
legacy agent_rader = preserved research/migration source
new agent-career-harness = product software repo
```

---

# 42. AI Coding Agent Protocol

任何 Claude/Codex 修改代码前先输出：

```text
Task Understanding
Phase
Relevant PRD Sections
Relevant Approved ADR
Relevant Project/Product Cards
Files to Change
Data Migration Impact
Security Impact
Test Plan
Rollback/Exit Path
```

禁止：

- 看见高 Star repo 就换 Core；
- 看见 Magic Resume 就 fork 整站；
- 看见 Agent Framework 就换 Runtime；
- 看见 browser agent 就启用 stealth/CAPTCHA；
- 看见 Feishu 就双写；
- 看见历史数据就批量搬目录；
- 未 reconciliation 就宣布 SQLite canonical；
- 未批准就改变 Hard Constraints。

---

# 43. Definition of Done — Product

完整闭环：

```text
用户设置目标
→ 观察 Source
→ 发现 Job/Change
→ 保存 Evidence
→ Opportunity
→ Match/Gap
→ Resume Patch
→ Human Review
→ ResumeRevision/PDF
→ Playwright Prepare
→ Human Submit
→ Interview/FollowUp/Outcome
→ Insights
→ Next Plan
```

任一步能回答：

```text
Where did this come from?
Which revision?
Which model?
Which adapter?
Who approved?
What happened next?
```

---

# 44. Definition of Done — Engineering & Safety

必须：

```text
Core tests
Schema versioning
DB migration
Artifact hashes
Backup/restore
Idempotent writes
Run audit
PII redaction
Environment isolation
Adapter contract tests
Desktop-sidecar lifecycle tests
Migration reconciliation
```

安全：

```text
TEST cannot enter PROD
Agent cannot approve own output
Signal cannot silently become Fact
Unknown legal field creates Blocker
Browser cannot autonomous final-submit
Feishu delete cannot delete Core
Feishu failure cannot corrupt Core
Credential/session never enters ordinary Artifact Store
```

---

# 45. Environment Model

Environment：

```text
TEST
STAGING
PROD
```

Data Class：

```text
TEST
REAL
```

合法：

```text
TEST + TEST
STAGING + REAL
PROD + REAL
```

禁止：

```text
PROD + TEST
```

TEST 不允许通过改标签变成 REAL。

---

# 46. Release Strategy

开发：

```text
React/Vite dev server
+
Python local API
```

Desktop dev：

```text
Tauri dev
+
Python sidecar
```

发布：

```text
Python backend
→ sidecar executable
→ Tauri bundle
```

P0 第一验证平台为当前实际开发环境 Windows；Core 不写死为 Windows-only。

---

# 47. Open Questions

以下不能由 Coding Agent 擅自决定：

1. 各数据级别 retention；
2. 敏感 Artifact 是否应用层加密；
3. Backup 介质；
4. Legacy 两套 Snapshot reconciliation 结果；
5. canonical opaque ID 最终格式；
6. ResumeContentSchema 最小字段；
7. P2 第一批 ATS；
8. Feishu PROD 是否需要实时 webhook；
9. Tauri auto-update 何时启用；
10. 何时支持第二真实用户。

---

# 48. Final Product Principle

> **Agent Career Harness 不是替用户多投简历，而是替用户维护一个可信、持续更新、能真正采取行动的职业系统。**

价值顺序：

```text
Truth
→ Context
→ Decision
→ Preparation
→ Execution
→ Outcome
→ Learning
```

而不是：

```text
More Agents
→ More Automation
→ More Applications
```

最终原则：

```text
Desktop is replaceable.
Models are replaceable.
Feishu is replaceable.
Parsers are replaceable.
Browsers are replaceable.
Renderers are replaceable.
Workflow runtimes are replaceable.

Evidence is not.
Candidate Facts are not.
Career History is not.
Approvals are not.
Audit is not.
Outcomes are not.
```

---

# 49. v1.2 Delta Summary

```text
KEEP:
Evidence/Fact/Signal/Decision/Outcome
ExtractedClaim
Revision/Event/Outbox
SQLite + Artifact Store
LocalStepRunner
Typed Adapter Ports
Playwright
Docling fallback routing
Resume Patch architecture
Feishu durable sync
P0A/P0B/P0C migration

CHANGE:
Feishu Human Workspace → Feishu Companion Workspace
Optional Review Console → Primary Desktop Application

ADD:
Tauri + React + Python sidecar
Discover
Watchlist
Quick Capture
Opportunity Dossier
Answer Bank
InterviewSession
Insights
New Repo Strategy
ADR-013/014/015/016
P0F/P0D

DO NOT CHANGE:
Truth ownership
HITL submission
No CAPTCHA/stealth/proxy
No auto-fabrication
No Big Bang rewrite
No premature multi-agent/plugin platform
```

**End of PRD v1.2**
