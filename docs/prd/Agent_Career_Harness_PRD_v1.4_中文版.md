# Agent Career Harness — Product & Implementation PRD v1.4

**版本**：v1.4  
**日期**：2026-09-18  
**状态**：产品方向收敛版 / 可进入下一轮原型与实现拆解  
**文档语言**：中文为主；必要的技术实体、协议、代码标识保留英文

---

## 0. 一句话定位

**Agent Career Harness 是一个面向 AI Engineer 求职市场、以 Agent Engineering 为最深垂直方向的本地优先 AI 职业工作台。**

它不以“岗位最多”为目标，而是围绕少量真正值得投入的机会，把用户从岗位发现一路推进到能力判断、项目增强、简历定制、面试准备、投递跟踪与结果沉淀。

更完整地说：

> **不是做一个 AI 岗位聚合器，而是建立 AI Engineer，尤其是 Agent Engineer 的职业能力模型，再把市场需求和个人真实资产连接起来。**

---

# 1. 产品愿景

传统招聘网站解决的是“外面有什么岗位”。

传统简历工具解决的是“怎么把一份简历写得更像样”。

传统 AI 助手解决的是“当前这个问题怎么回答”。

Agent Career Harness 要解决的是更长周期的问题：

> **我是谁、我已经有什么、市场正在要什么、我真正想去哪里，以及我下一步最值得做什么。**

产品的目标不是替用户“找到更多岗位”，而是：

> **帮用户把少量真正值得投的 AI / Agent 岗位，从发现一路推进到结果。**

因此，产品应长期维护并连接：

- Personal Context：我是谁；
- Career State：我现在处于什么状态；
- Project Evidence：我真正做过什么；
- Market Evidence：外面的岗位和市场正在发生什么；
- Career History / Outcomes：过去什么行动产生了什么结果。

中间由：

- Context Compiler；
- Career Reasoning；

不断把这些长期资产转化为：

- 下一步行动；
- 能力投资计划；
- 项目增强任务；
- Resume Patch；
- Interview Prep；
- Application / Outcome 更新。

---

# 2. 核心产品原则

## 2.1 Local-first

用户长期职业数据默认以本地 Career Core 为 canonical truth。

模型、浏览器工具、飞书、Coding Agent、MCP、Skills、CLI、外部服务都只能作为能力来源，不拥有用户的长期真相。

## 2.2 Evidence-constrained

正式事实、简历内容、项目能力、求职状态应尽量有来源。

AI 可以提取、推断、建议、组织、生成候选内容，但 AI 不应未经确认把推断直接升级成正式事实。

核心原则：

> **AI 可以提议，但不能偷偷创造你的过去。**

## 2.3 Human-in-the-loop

高影响决策由 AI 提议、用户确认。

例如：

- 是否把岗位加入 Opportunity；
- 是否修改最终 Opportunity 优先级；
- 是否把 AI 推断升级为 Career Fact；
- 是否采用 Resume Patch；
- 是否合并 Coding Agent 的项目改造；
- 是否把 Candidate Capability Node 写入正式 Capability Graph。

统一边界：

```text
AI 负责：
观察
分析
提取
建议
推荐

用户负责：
确认
覆盖
最终选择
```

## 2.4 Stable Core, Pluggable Execution

核心长期资产稳定，执行能力可替换。

> **核心固定，执行能力可插拔。**

可替换部分包括：

- LLM；
- Browser Worker；
- Claude Code / Codex CLI；
- MCP Server；
- Skill；
- Feishu；
- Renderer；
- Parser；
- External Search；
- Workflow Runtime。

不可被插件拥有的部分包括：

- Personal Context；
- Candidate Facts；
- Career State；
- Project Evidence；
- Capability State；
- Approvals；
- Career History；
- Outcomes；
- Audit。

## 2.5 Replayable and Auditable

关键状态变化应尽量可解释、可回放、可追踪。

系统应记录：

- 来源；
- 时间；
- 触发原因；
- 使用过的上下文；
- AI 建议；
- 用户确认 / override；
- 最终结果。

---

# 3. 产品差异化

## 3.1 不和通用招聘平台比“岗位多”

类似通用招聘聚合器的产品往往：

```text
岗位很多
↓
用户自己筛
↓
自己判断
↓
自己改简历
↓
自己准备面试
```

Agent Career Harness 的目标流程是：

```text
重点收集 AI / Agent 相关岗位
↓
理解 JD 到底在要什么
↓
结合“我是谁 + 我有什么项目 + 我想去哪里”
↓
判断是否值得进入 Opportunity
↓
发现能力 Gap
↓
决定哪些 Gap 值得投资
↓
改造已有项目
↓
形成新的 Project Evidence
↓
针对 JD 生成 Resume Patch
↓
做 Interview Prep
↓
维护 Application / Interview / Outcome
```

因此产品竞争力不只是“岗位数据量”，而是：

> **对 AI Engineer，尤其 Agent Engineer 岗位的结构化理解，以及把这种理解与个人长期资产连接起来的能力。**

## 3.2 岗位范围：宽覆盖，深度分层

产品不是只支持岗位名称中含有 “Agent Engineer” 的职位。

采用以 Agent 为中心的同心圆：

### 第一层：核心 Agent 岗位

- Agent Engineer
- AI Agent Engineer
- Agent Platform Engineer
- Agent Infra Engineer

最深的岗位结构与能力建模。

### 第二层：强相关 AI Engineering

- AI Infra Engineer
- LLM Engineer
- RAG Engineer
- AI Backend Engineer
- LLM Platform Engineer
- Applied AI Engineer
- AI Application Engineer

作为主要相邻市场。

### 第三层：更广泛 AI 岗位

- AI Algorithm Engineer
- Prompt Engineer
- AI Application
- 模型应用工程师
- 其他 AI Engineer

主要用于探索、市场趋势和相邻机会发现。

核心原则：

> **岗位范围宽，能力模型深度有层级。**

---

# 4. 五类长期资产

## 4.1 Personal Context

回答：

> 我是谁？

包括：

- 经历；
- 技能；
- 教育；
- 偏好；
- 地点；
- 目标；
- 方向兴趣；
- 约束；
- 近期方向变化；
- AI 对用户的可解释理解。

## 4.2 Career State

回答：

> 我现在在找什么、投到哪里、进展怎样？

包括：

- Watchlist；
- Opportunity；
- Application；
- Interview；
- Offer；
- Rejection；
- Follow-up；
- Deadline；
- 当前优先级；
- 下一步动作。

## 4.3 Project Evidence

回答：

> 我真正做过什么？

```text
项目源码
↓
用户指定扫描范围
↓
一次扫描 / 增量扫描
↓
项目证据资产
↓
长期缓存
↓
按 JD 复用
```

## 4.4 Market Evidence

回答：

> 外面的岗位与市场发生了什么？

进一步分为两层。

### Target Market Evidence

真正与用户相关的目标市场。

来源：

- 用户主动收藏的岗位；
- 用户确认进入 Opportunity 的岗位；
- 用户明确感兴趣的公司；
- 用户明确感兴趣的方向。

作用：

- Capability Investment Planning；
- Project Enhancement 优先级；
- Resume / Interview Prep；
- Career Reasoning。

### Broad Market Trend

更广泛市场趋势。

来源：

- 自动采集的大量岗位；
- 行业变化；
- 公司招聘趋势；
- 技术关键词变化。

作用：

- 看行业发生什么；
- 发现新方向；
- 校验个人视野；
- 作为探索信号。

原则：

> **市场告诉你“外面发生了什么”，但不能替你决定“你应该成为什么”。**

## 4.5 Career History / Outcomes

回答：

> 过去什么行动产生了什么结果？

包括：

- 投递；
- 面试；
- Offer；
- Rejection；
- Resume Revision；
- Project Enhancement；
- 学习任务；
- 某次能力投资；
- 最终反馈。

这些结果反过来更新 Career Reasoning、Priority、Capability Investment 和 Personal Context。

---

# 5. Context Compiler

## 5.1 定位

Memory 负责：

> 记住什么。

Context Compiler 负责：

> 这一次应该想起什么。

推荐流程：

```text
Long-term Context
↓
Relevance Selection
↓
Evidence-aware Compression
↓
Vertical Knowledge Injection
↓
Task Context Assembly
↓
Context Manifest
↓
Model
```

中文表达：

```text
长期上下文
↓
相关性筛选
↓
带来源的压缩
↓
垂直领域知识注入
↓
任务上下文组装
↓
记录本次上下文清单
↓
交给模型
```

## 5.2 Context Manifest

每次重要 AI 调用应尽量记录：

- 使用了哪些 Personal Context；
- 使用了哪些 Project Evidence；
- 使用了哪些 Market Evidence；
- 使用了哪些 Career History；
- 哪些内容被排除；
- 使用了哪个模型；
- 使用了什么 Skill / Capability。

用户可查看：

> Preview AI Context

避免“上下文到底用了什么”变成黑盒。

---

# 6. 岗位漏斗

岗位状态采用明确漏斗：

```text
Broad Market
全市场岗位
↓
Discover
系统发现的岗位
↓
Watchlist
我觉得有点意思，先关注
↓
Opportunity
我确认：值得认真研究
↓
Application
我真的开始准备 / 投递
```

## 6.1 Discover

系统自动发现岗位。

AI 可以：

- 抓取；
- 去重；
- JD 解析；
- 基础相关性判断；
- 推荐进入 Watchlist / Opportunity。

## 6.2 Watchlist

含义：

> 我有兴趣，但暂时不值得投入很多精力。

## 6.3 Opportunity

含义：

> 如果条件合适，我真的会考虑投，并愿意为它投入时间。

进入 Opportunity 后，才触发更重动作：

```text
JD 深度解析
↓
Match / Gap
↓
Project Evidence 检索
↓
Capability Investment 影响
↓
Resume Patch
↓
Interview Prep
```

## 6.4 Opportunity 进入规则

采用：

> **AI 推荐 + 用户确认**

AI 可以根据 Personal Context、Match、Target Market Evidence、兴趣、项目证据、地点和岗位方向给出“建议加入 Opportunity”，但必须由用户确认后才能正式进入。

同时保留手动入口：

- 手动收藏；
- 手动加入 Opportunity；
- 手动录入 JD。

---

# 7. Opportunity Priority

## 7.1 Priority 不等于 Match

必须区分：

```text
Match
我和岗位有多匹配

Priority
这个岗位现在值不值得投入
```

## 7.2 Suggested Priority 与 User Priority

Opportunity 中同时保存：

### Suggested Priority

系统建议优先级。

### User Priority

用户最终确认优先级。

例如：

```text
系统建议优先级：高

主要原因：
✓ 目标岗位方向高度一致
✓ 地点符合偏好
✓ 现有项目匹配度高
✓ 当前只需少量补强
△ 薪资信息不明确
△ 岗位发布时间较早

用户优先级：
高 [可修改]
```

## 7.3 动态重算

系统可根据快截止、面试临近、岗位下线、很久没有回复、新出现更好的岗位、用户目标变化、Application 状态变化，动态重算 Suggested Priority。

但：

> **User Priority 不自动改变。**

系统只：

```text
重新计算 Suggested Priority
↓
告诉用户为什么变了
↓
建议重新排序
↓
等待用户确认
```

---

# 8. Today：动态职业行动队列

首页不应只是聊天框，也不应只是待办列表。

Today 应回答：

> **今天最值得做什么？**

示例：

```text
今天优先处理
────────────────

1. 字节 Agent Engineer
   用户优先级：高
   系统建议：高 → 紧急
   原因：2 天后截止
   下一步：完成 Resume Patch

2. 腾讯 AI Infra
   用户优先级：高
   系统建议：高
   原因：明天面试
   下一步：完成 Interview Prep

3. Startup X
   用户优先级：中
   系统建议：中 → 低
   原因：岗位已发布 28 天
   下一步：建议降低投入

4. agent-gateway 项目增强
   来源：12 个 Target Opportunity 的共性 Gap
   下一步：补充 Observability
```

Today 的排序应综合：

- User Priority；
- Suggested Priority；
- 截止时间；
- Interview 时间；
- Opportunity 阶段；
- 能力投资价值；
- 当前待办依赖；
- 用户目标。

---

# 9. Personal Capability Graph

## 9.1 为什么不是单独的岗位能力树

不同 AI 岗位共享大量基础能力。

因此底层应采用：

> **Capability Graph，而不是互相孤立的岗位能力树。**

## 9.2 三层能力结构

### 第一层：AI Engineer Common Core

- Python；
- Backend Engineering；
- API / Async；
- Database / Cache；
- Testing；
- System Design；
- LLM Fundamentals；
- Evaluation；
- Git / Engineering Practice；
- Observability；
- Security Basics。

### 第二层：Track Capability

#### Agent Engineering

- Tool Calling；
- MCP；
- Context Engineering；
- Memory；
- Agent Runtime；
- Multi-Agent。

#### AI Infra

- Model Serving；
- Distributed Systems；
- Kubernetes；
- GPU / Inference；
- Observability。

#### RAG

- Retrieval；
- Chunking；
- Reranking；
- Vector DB；
- RAG Evaluation。

#### Applied AI

- Model API；
- Prompt / Context；
- Product Integration；
- Evaluation；
- Guardrails。

### 第三层：Opportunity Specific Capability

某一个具体 JD 的专项能力，例如：

- Ray；
- LangGraph；
- OpenTelemetry；
- 某特定推理框架；
- 某公司内部技术栈的相邻能力。

---

# 10. Official Capability Graph + Personal Capability Overlay

## 10.1 两张逻辑分离、运行时叠加的图

```text
Official Capability Graph
官方基础能力图谱
        +
Personal Capability Overlay
个人能力覆盖层
        +
Target Market Evidence
        ↓
Personal Capability Graph
```

## 10.2 Official Capability Graph

特点：

- 稳定；
- 可解释；
- 有版本；
- 可以开源；
- 可以由社区贡献；
- 不依赖某个具体用户。

它定义：

> 地图长什么样。

## 10.3 Personal Capability Overlay

记录：

- 这个能力我会不会；
- 理解到什么程度；
- 能不能讲；
- 有没有做过；
- 有没有证据；
- 是否 Resume Ready；
- 是否愿意继续投入；
- 当前 Opportunity 是否需要；
- 最近有没有验证。

它定义：

> 我现在站在哪里。

---

# 11. Capability Graph 的五层数据模型

建议拆成：

```text
1. Capability Ontology
   这个行业有哪些能力

2. Personal Capability State
   我在每个能力节点上处于什么状态

3. Evidence Binding
   什么项目 / 经历证明我有这个能力

4. Market Binding
   哪些 JD 正在要求这个能力

5. Investment State
   这个能力现在值不值得投入
```

## 11.1 示例：Observability

```text
Observability
──────────────────

所属方向
AI Engineer Common Core
AI Infra
Agent Platform

市场
12 / 20 Target Opportunities 要求

个人状态
已了解

Project Evidence
agent-gateway:
- logging ✓
- tracing ×
- metrics △

能力缺口
Tracing / OpenTelemetry

投资价值
高

建议动作
Project Enhancement Task:
在 agent-gateway 中增加 OpenTelemetry tracing
```

这个页面应同时回答：

- 市场要不要？
- 我会不会？
- 我有什么证据？
- 我值不值得学？
- 下一步应该做什么？

---

# 12. Capability Graph 初始化与增量更新

## 12.1 init + incremental update

借鉴 CodeGraph 一类“先初始化，再增量更新”的思想：

```text
初始化
↓
项目内置 / 人工定义的基础能力图谱
↓
Capability Graph v1.0

新的 JD / Project / Market Evidence
↓
AI 发现新概念
↓
Candidate Capability Node
↓
规则校验 / 用户确认
↓
增量写入
↓
Capability Graph v1.1
```

原则：

> **AI 可以发现，不能随意定义。**

## 12.2 Capability Inbox

AI 发现新能力后，先进入暂存区：

```text
Capability Inbox
────────────────

Agentic RAG

出现：17 个 JD

建议归属：
RAG
Agent Engineering

可能重复：
Agentic Retrieval

[接受]
[合并]
[忽略]
[稍后]
```

## 12.3 Versioning

能力图谱应版本化：

```text
Capability Graph v1.0
↓
+ Agent Evaluation
+ MCP Security
- 合并 Prompt Engineering / Prompt Design
↓
Capability Graph v1.1
```

官方图谱升级不应破坏 Personal Capability Overlay。

---

# 13. Personal Capability State

底层采用多维状态，界面显示简单状态。

建议底层维度包括：

- Understand：是否真正理解；
- Explain：是否能在面试中讲清楚；
- Apply：是否实际做过；
- Evidence：是否有可验证证据；
- Interview Ready：是否敢写进简历并接受追问。

系统再推导简单状态：

```text
Unknown
↓
Understood
↓
Practiced
↓
Applied
↓
Verified
↓
Resume Ready
```

原则：

> **不要把“这个人的能力模型”绑定在某次 AI 推理结果上。**

模型只是帮助维护图谱的人，图谱本身是长期资产。

---

# 14. Capability Investment Planning

## 14.1 核心问题

不是：

> 哪个技能出现次数最多？

而是：

> **下一笔时间应该投资到能力图谱的哪个节点上？**

## 14.2 决策因素

能力投资价值可以综合：

```text
目标市场需求
× 岗位重要性
× 跨岗位复用度
× 与现有项目接近程度
× 可形成证据的可能性
× 个人兴趣
÷ 学习 / 改造成本
```

第一版不要求严格数学化，但逻辑应保留。

## 14.3 二八原则

优先多个高优先级 Target Opportunity 中的共性能力。

长尾能力只有在以下情况下重点投入：

- 用户特别喜欢某个岗位；
- 某家公司优先级极高；
- 该能力有较大长期迁移价值。

## 14.4 两层能力投资

### Core Capability Roadmap

回答：

> 未来 1–3 个月，我最值得投资哪些可复用能力？

### Per-Job Tailoring

回答：

> 为了某个特别重要的岗位，我还要做什么专项强化？

---

# 15. Match / Gap 重新定义

不要只输出：

> Match Score = 72%

更有用的结构是：

```text
已覆盖
✓ Python
✓ RAG
✓ Redis
✓ Streaming

可快速补强
△ Circuit Breaker Benchmark
△ Multi-model Routing
△ Observability

明显缺口
× Kubernetes
× Production deployment
```

用户真正关心的是：

> **我接下来做什么，能最快把自己变得更适合这个岗位？**

---

# 16. Project Evidence Library

## 16.1 目标

```text
项目源码
↓
一次扫描
↓
Project Evidence
↓
长期缓存 / 可复用
↓
JD 到来
↓
只检索相关项目证据
↓
生成 Match / Gap / Resume Patch
```

## 16.2 扫描范围由用户控制

默认不做全盘扫描。

```text
用户选择项目
↓
用户指定允许扫描范围
↓
Project Scanner
↓
项目证据资产
↓
长期缓存
```

示例：

```text
允许：
src/
docs/
README.md
pyproject.toml
package.json

禁止：
.env
secrets/
data/
logs/
build/
```

原则：

> **默认可控，而不是默认全读。**

## 16.3 项目证据目录

推荐：

```text
project_evidence/
├── agent-gateway/
│   ├── project_profile.md
│   ├── technical_evidence.md
│   ├── achievements.md
│   ├── resume_materials.md
│   └── source_manifest.json
└── rag-system/
```

与外部参考分离：

```text
references/
```

## 16.4 Evidence Authority

项目证据来源区分：

- Code Verified；
- Document Supported；
- User Confirmed；
- AI Inferred。

技术事实可被代码直接证明时，可以自动进入较高可信状态。

但以下内容不能仅由代码自动确认：

- 性能提升；
- 业务结果；
- 个人贡献比例；
- “独立设计 / 独立实现”；
- 成功率；
- 用户量；
- 延迟改善。

需要测试、Benchmark、文档、报告或用户确认。

---

# 17. Project Capability State

对于项目里的某项能力，应区分：

```text
Existing
项目里存在

Understood
用户真正理解

Modified
用户修改过

Extended
用户新增过

Validated
用户跑过测试 / Benchmark

Resume Ready
证据足够，可用于正式简历
```

原则：

> 项目里有，不等于用户会；  
> 用户看懂了，也不等于用户做过；  
> 用户做过，也不一定已经有足够证据写进简历。

---

# 18. Project Enhancement Loop

这是产品的重要核心闭环：

```text
JD
↓
岗位能力拆解
↓
和已有 Project Evidence 比较
↓
发现 Gap
↓
判断 Gap 是否可以在熟悉项目中补强
↓
生成 Project Enhancement Task
↓
学习 / 改代码 / 做实验 / 补文档
↓
重新扫描与验证
↓
形成新的 Project Evidence
↓
进入 Career Fact
↓
Resume Material
↓
Interview Talking Point
↓
针对该 JD 的 Resume Patch
```

核心价值：

> **把现有项目持续改造成更适合目标岗位的职业资产。**

这本质上仍然是一种“包装”，但必须是：

> **有依据的包装。**

更正式的表述：

> **Evidence-grounded Positioning：证据约束的针对性表达。**

---

# 19. Project Enhancement Task

例如：

```text
△ Observability

推荐项目
agent-gateway

为什么推荐
你已经熟悉该项目的请求链路和模型路由，
在这里增加 tracing 的学习成本最低。

增强任务
1. 梳理 request → router → provider 调用链
2. 接入 OpenTelemetry tracing
3. 记录首包延迟 / 总延迟
4. 增加模型切换 span
5. 编写测试
6. 更新架构说明
7. 重新扫描项目

完成后可沉淀
- Project Evidence
- Resume Material
- Interview Talking Point
- JD Match Improvement
```

---

# 20. Project Enhancement Executor

谁来执行应是可替换的。

```text
JD Gap
↓
Project Enhancement Task
↓
选择执行方式
├─ 我自己做
├─ AI 分析 + 给方案 / Diff
└─ Coding Agent 自动改造
↓
验证
↓
重新扫描
↓
Project Evidence
```

## 20.1 三个执行级别

### L1 建议模式

Harness：

- 分析项目；
- 生成学习任务；
- 生成修改建议；
- 生成实验方案。

适合 MVP。

### L2 协作模式

调用本机 Coding Agent：

- Claude Code；
- Codex；
- 其他 CLI；

完成代码分析、方案与 Diff，由用户修改 / 确认。

### L3 执行模式

经用户确认后：

- 创建独立 branch / worktree；
- 调用 Coding Agent 自动修改；
- 运行测试；
- 生成文档；
- 输出 Diff；
- 输出测试结果；
- 输出新 Project Evidence 候选；
- 等待用户决定是否合并。

## 20.2 Local Coding Executor / CLI Adapter

第一版无需自建完整 Coding Agent 平台。

```text
Project Enhancement Task
↓
Executor Router
├─ Manual Executor
├─ Claude Code CLI Adapter
├─ Codex CLI Adapter
└─ Future MCP / Remote Coding Agent
↓
Diff / Test / Logs / Docs
↓
用户审核
↓
重新扫描
↓
Project Evidence
```

原则：

> **Harness 管任务和边界，CLI 负责执行。**

Coding Agent 是执行能力，不是事实权威。

---

# 21. Resume Truth Model

不维护大量互相独立、互相漂移的简历真相。

采用：

```text
Base Resume
↓
JD A Resume Patch
↓
ResumeRevision A

Base Resume
↓
JD B Resume Patch
↓
ResumeRevision B
```

Resume Patch 只消费合格事实和证据。

```text
AI Inferred
↓
不能直接用于正式简历
↓
补证据 / 用户确认
↓
Verified Evidence
↓
Career Fact
↓
Resume Patch
```

---

# 22. Career Reasoning

Career Reasoning 不只是：

> 这个岗位适不适合我？

还要回答：

> **我有限的时间下一步投资在哪里，收益最高？**

输入：

```text
Market Evidence
+
Opportunity
+
Personal Context
+
Project Evidence
+
Career History / Outcomes
```

输出：

```text
Career Reasoning
↓
Personal Capability Graph
↓
Capability Investment Plan
↓
Project Enhancement Task / Learning Task
↓
Resume / Interview / Action
```

---

# 23. UI / Information Architecture

建议一级导航：

```text
Today
Opportunities
Projects
Capabilities
Resume
History
Me / Context
Settings
```

## 23.1 Today

动态职业行动队列。

## 23.2 Opportunities

包含：

- Discover；
- Watchlist；
- Opportunity；
- Application。

支持：

- AI 推荐；
- 手动添加；
- 筛选；
- 公司 / 地点 / 技术方向浏览；
- Suggested Priority；
- User Priority；
- Match / Gap；
- 下一步行动。

可以借鉴通用招聘产品的列表、卡片、筛选形式，但保持 AI / Agent 岗位垂直化。

## 23.3 Projects

显示：

- 已连接项目；
- 扫描范围；
- Project Evidence；
- Project Capability State；
- Project Enhancement Task；
- 增量扫描状态。

## 23.4 Capabilities

应提供 Capability Graph 可视化。

用户可以看到：

```text
Official Capability Graph
+
Personal Capability Overlay
+
Market Demand
+
Investment Priority
```

能力节点建议显示：

- 所属方向；
- 个人状态；
- Evidence；
- JD 覆盖；
- Investment Priority；
- 下一步任务。

## 23.5 Me / Context

不要叫黑盒式“Memory 管理”。

推荐：

```text
我的事实
我的经历
我的技能
我的目标
我的偏好
AI 对我的理解
当前求职状态
过去的重要结果
```

---

# 24. 本地数据目录

代码仓库与用户数据分离。

```text
agent-career-harness/
```

和：

```text
AgentCareerHarnessData/
├── core.db
├── artifacts/
├── sessions/
├── extensions/
├── project_evidence/
├── references/
├── context_exports/
├── backups/
└── logs/
```

## 24.1 core.db

保存结构化 canonical truth。

## 24.2 context_exports

可选人类可读导出：

```text
context_exports/
├── profile.md
├── preferences.md
├── goals.md
├── memories.md
└── career_history.md
```

这些是便携导出，不是 canonical truth。

---

# 25. Extension / Skill / MCP 模型

## 25.1 定义

### Plugin
安装、启用、禁用、组合能力的包装单元。

### Skill
完成某类任务的方法：instructions、workflow、templates、required capabilities。

### Tool
原子动作。

### MCP
外部能力连接协议之一。

### Adapter
Harness 对某个具体实现的兼容层。

### Capability
抽象的可调用能力。

## 25.2 Skill 不拥有 Provider

Skill 依赖抽象 Capability。

例如：

```text
GitHub Research Skill

requires:
- repository_search
- repository_read
- web_search
```

具体可以由 GitHub MCP、REST Adapter、Browser 或 Local Tool 提供。

## 25.3 Extension 边界

Extension 不应：

- 拥有 canonical truth；
- 静默修改 Career Fact；
- 绕过审批；
- 绕过权限；
- 删除后导致 Career Core 不可用。

---

# 26. 外部工具定位

## 26.1 Browser / 豆包工作

当前可继续作为 Browser Collector。

统一输出到：

```text
Capture / Evidence Contract
```

后续可以替换为 Playwright、Browser Adapter 或其他浏览器 Worker。

## 26.2 Feishu

定位：

> Companion / Projection

不是 canonical database。

## 26.3 Claude Code / Codex

定位：

> Enhancement Executor

不是 Career Core。

---

# 27. 安全与权限

## 27.1 项目扫描

采用最小访问原则。

## 27.2 CLI Executor

每个任务应明确：

- working directory；
- allowed files；
- denied files；
- 是否允许写；
- 是否允许 shell；
- 是否允许网络；
- 是否需要 branch / worktree；
- 最大执行范围。

## 27.3 高影响动作

默认需要用户确认：

- 正式投递；
- 简历正式生成；
- 修改 Career Fact；
- 合并代码；
- 修改 User Priority；
- 写入 Capability Ontology；
- 删除 Evidence。

---

# 28. MVP

MVP 不应一次做成完整职业 OS。

采用：

> **Harness Kernel MVP + Career Vertical Slice**

## 28.1 P0：Kernel

必须有：

- Local Career Core；
- SQLite；
- Artifact Store；
- basic audit；
- Capability Registry；
- Context Compiler 基础版；
- Adapter 基础接口；
- Personal Context；
- Project Evidence；
- Career State。

## 28.2 P0 Career Vertical Slice

至少跑通：

```text
Job / Capture
↓
Evidence
↓
Opportunity
↓
Match / Gap
↓
Project Evidence
↓
Resume Patch
↓
Human Review
↓
ResumeRevision
↓
Application Record
↓
Outcome
```

## 28.3 P0 Capability Slice

至少跑通：

```text
Official Capability Graph
↓
Personal Capability Overlay
↓
Target Opportunity
↓
Market Binding
↓
Capability Gap
↓
Capability Investment Suggestion
```

第一版 Capability Graph 可先做静态基础图 + 简单节点状态，不必一开始实现复杂图数据库。

## 28.4 P0 Project Enhancement

只做 L1：

```text
Gap
↓
Project Enhancement Task
↓
告诉用户：
要学什么
看哪些文件
改哪里
怎么验证
完成后能形成什么 Resume Material
```

## 28.5 P1

加入：

- Claude Code / Codex CLI Adapter；
- Capability Inbox；
- 增量 Project Scan；
- Suggested Priority 动态重算；
- Today Action Queue；
- Broad Market Trend；
- Capability Graph 可视化。

## 28.6 P2

加入：

- L3 Coding Executor；
- branch / worktree 自动执行；
- 自动测试；
- 自动文档；
- Capability Graph versioning；
- 更完整的 Career Reasoning；
- Outcome-driven Recommendation。

---

# 29. MVP 可插拔性验证

必须能够证明：

1. 关闭 Feishu，Career Core 仍能工作；
2. 关闭 GitHub 集成，Career Core 仍能工作；
3. 替换 Browser Worker，Job / Evidence contract 不变；
4. 替换 LLM，Personal Context / Facts / Career History 不丢；
5. 安装 Skill，不需要修改 Kernel；
6. 删除 Skill，canonical data 不丢；
7. 不安装 Claude Code / Codex，也能完成 L1 Project Enhancement；
8. 替换 Coding Executor，Project Enhancement Task contract 不变。

---

# 30. 非目标

当前阶段明确不做：

- 通用招聘网站；
- 所有行业岗位聚合；
- 公共插件市场；
- 通用多 Agent 平台；
- 完整 IDE；
- 自研 Coding Agent；
- 自动无审批投递；
- 完全自动修改 Career Fact；
- AI 随意重写 Capability Graph；
- 为每个 JD 建立完全独立的能力体系。

---

# 31. 核心数据对象建议

建议核心对象至少包括：

```text
PersonalContext
CandidateFact
Evidence
ExtractedClaim
FactProposal

Job
WatchlistItem
Opportunity
Application
Interview
Outcome

Project
ProjectScanScope
ProjectEvidence
ProjectCapabilityState
ProjectEnhancementTask

CapabilityNode
CapabilityRelation
CapabilityGraphVersion
CandidateCapabilityNode
PersonalCapabilityState
EvidenceBinding
MarketBinding
InvestmentState

ResumeBase
ResumePatch
ResumeRevision
ResumeRender

ContextManifest
SuggestedPriority
UserPriority
DomainEvent
Approval
AuditLog
```

---

# 32. 最重要的产品闭环

## 32.1 岗位闭环

```text
发现岗位
↓
用户确认 Opportunity
↓
Match / Gap
↓
Resume / Interview
↓
Application
↓
Outcome
↓
Career History
```

## 32.2 能力成长闭环

```text
Target Opportunities
↓
Capability Gap
↓
Capability Investment Planning
↓
Learning / Project Enhancement
↓
Evidence
↓
Personal Capability State
↓
Resume Ready
```

## 32.3 项目资产闭环

```text
Project
↓
Scan
↓
Project Evidence
↓
JD Match
↓
Project Enhancement
↓
Re-scan
↓
New Evidence
```

## 32.4 长期学习闭环

```text
行动
↓
结果
↓
Career History / Outcomes
↓
Career Reasoning
↓
下一次更好的行动
```

---

# 33. 当前产品核心结论

Agent Career Harness 不只是：

- 招聘信息聚合；
- 简历生成器；
- 面试助手；
- AI 聊天工具；
- Memory 工具；
- Coding Agent。

它更接近：

> **一个本地优先、证据约束、长期维护个人职业状态，并通过可插拔 AI 能力持续把市场变化转化为下一步行动的 AI Career Workspace。**

在 AI Engineer / Agent Engineer 这个垂直方向，它最核心的差异化不是“知道更多岗位”，而是：

1. 理解岗位；
2. 理解用户；
3. 理解用户真实项目；
4. 理解能力缺口；
5. 判断什么值得投入；
6. 把 Gap 转成学习 / 项目增强任务；
7. 把增强结果重新沉淀成 Evidence；
8. 把 Evidence 转成 Resume / Interview / Application；
9. 把 Outcome 再反馈给系统。

最终形成：

```text
市场需要什么
+
我现在有什么
+
我过去做过什么
+
我想去哪里
↓
下一步最值得做什么
```

这应成为 Agent Career Harness 的长期智能核心。
