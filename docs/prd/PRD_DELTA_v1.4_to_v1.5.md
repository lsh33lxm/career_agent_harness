# PRD v1.4 → v1.5：实现事实与候选增量

日期：2026-09-21。观察基点：`cee9162`。
状态：**companion / PROPOSED 产品增量**，不是已批准的新 PRD，也不替换 [v1.4 中文原文](Agent_Career_Harness_PRD_v1.4_中文版.md)。已经冻结的实现边界仍以 shared contracts / decisions 为准，本文不授予新增 canonical authority。

## 1. 不变原则

Local-first；Evidence != Fact != Signal != Decision != Outcome；ExtractedClaim 需显式 promotion；Official Graph != Personal Overlay；SuggestedPriority != UserPriority；项目存在不等于个人掌握；Prepared != Submitted；用户控制身份及高影响决定。外部客户端/Feishu 不拥有 truth，Coding Agent 输出不是 Resume Fact。历史引用保持 exact revisions，dangling provenance 应显式失败。

## 2. 已核实的实现状态（不是新增产品批准）

| v1.4 章节/主题 | `cee9162` 代码事实 | 尚未完成或不应暗示 |
| --- | --- | --- |
| §24 本地数据目录 | [AppPaths](../../backend/career_harness/platform/paths.py) 使用 `ACH_DATA_DIR` override；Windows 默认 `%LOCALAPPDATA%/AgentCareerHarness`；数据库文件 `career_harness.db`；另有 `artifacts/`、`backups/`、`browser-sessions/`、`logs/` | PRD 示例的 `AgentCareerHarnessData/core.db` 不是当前默认落点；目录存在不代表 legacy canonical cutover |
| §31 核心对象 | migrations 已有 `0001` ～ `0013`，含下表所列业务持久化 | 旧迁移方案“仅 foundation，需要新建 migration 0002”已过期；不能据旧方案重建平行模型 |
| §8/§23 Today | [TodayPage](../../apps/desktop/src/pages/TodayPage.tsx) 消费真实 Core 队列，保留系统/用户优先级；六区包括首项展示、队列、待确认投影、明确 unavailable 的周回看与收集 | 首项展示没有新增 ranking；收集和周统计未接入；不虚构数据 |
| §23 Opportunities | 已有 [OpportunitiesPage](../../apps/desktop/src/pages/OpportunitiesPage.tsx) admission/priority 客户端 | 不能等同全量 Discover、Match 流程或真实 ATS 提交已完成 |
| §10/§12/§23 Capabilities | [CapabilitiesPage](../../apps/desktop/src/pages/CapabilitiesPage.tsx) 只读 workspace；[Inbox](../../apps/desktop/src/pages/CapabilityInboxPage.tsx) 执行已有用户 review 契约，保留已提交 candidate/graph query | UI 不能自动建立 Official Graph、个人掌握或用户优先级 |
| §23/§32 History | [HistoryPage](../../apps/desktop/src/pages/HistoryPage.tsx) 使用既有只读 Application/Outcome API，分开当前申请状态和历史 exact application revision/authority/evidence | 不从当前阶段推断 Outcome，不是 legacy 面经入个人历史的入口 |
| §23 其余入口 | [App.tsx](../../apps/desktop/src/app/App.tsx) 的 Projects、Resume、Me/Context、Settings 仍为 SectionPage 占位 | 有后端模型/服务不等于对应完整 UI 已交付 |
| §20 Executor | 已有 L1 offline acceptance 与 L2 explicit-context preparation | preparation 不等于已执行 Coding Agent；不声称 L3、外部 CLI 自动改造或真实部署完成 |
| §26 Feishu | 当前归档契约定义客户端/投影边界 | 本文未执行或验证外部 Feishu 写入；凭据/写入授权另行处理 |
| legacy preservation | `0.17.0` / D-027 已冻结 archive/disposable rehearsal 边界；fresh inventory 2426 文件通过检查 | 本基点不声称真实 archive/import/backup/restore 验收成功，不声称 canonical cutover |

### 已有 schema revision 链

以下是仓库 migration 文件存在性的核实，**不是对当前生产数据库已应用版本的声明**：

| Revision | 文件/职责 |
| --- | --- |
| 0001 | `0001_foundation.py`：基础实体/修订/事件边界 |
| 0002 | `0002_opportunity_core.py`：Opportunity |
| 0003 | `0003_capability_core.py`：Capability |
| 0004 | `0004_project_evidence.py`：Project Evidence |
| 0005 | `0005_context_manifest.py`：Context Manifest |
| 0006 | `0006_capability_personal_state_identity.py`：Personal State identity |
| 0007 | `0007_evidence_provenance.py`：Evidence provenance |
| 0008 | `0008_job_requirement_persistence.py`：Job/Requirement |
| 0009 | `0009_match_gap_persistence.py`：Match/Gap |
| 0010 | `0010_fact_promotion.py`：Fact promotion |
| 0011 | `0011_resume_core.py`：Resume |
| 0012 | `0012_application_outcome.py`：Application/Outcome |
| 0013 | `0013_interview_core.py`：Interview |

路径均在 `migrations/versions/`。新工作应复用现有模型和服务，不把 legacy 数据模型整体复制成另一个 Career Core。

## 3. 数据驱动的 v1.5 候选增量

本节所有量化依据来自 [DATA_BASELINE_v1.0](DATA_BASELINE_v1.0.md)；其 §1 manifest hash 固定每个 source 版本。建议被接受前仍标为 PROPOSED。

| 候选变更 | 实际触发依据 | 最小验收边界 |
| --- | --- | --- |
| 增加“观察粒度”显式标签 | `data/统一数据/岗位与JD数据.csv` 492 行包含 72 个岗位族聚合 | staging/导出同时显示原行数、粒度和已证明的去重范围；聚合不能冒充单岗位 |
| 来源等级按原值保存，单列 Core authority | `work/clean/interviews.json` → normalized 有 B→A 29、D→C 15；35 同 URL JD 为 S/C 冲突 | 保留原等级、转换来源与未决冲突；无自动 Fact/Official promotion |
| 增量按 exact mapping version 对账 | `new_question_occurrences.jsonl` 的 121 IDs 已存在，其中 82 个 canonical_question_id 不同 | 禁止重复 append 或覆盖历史；记录差异、版本、候选 disposition |
| 显式区分事件/发布/采集日期 | CN 面经 actual interview_date 213 空、4 非日级；CN 35 JD published_at 全空 | 缺失/精度可见；time weight 不能悄悄把 collected_at 变为 occurred_at |
| 个人练习计划与完成证据分离 | 270 个人刷题行均未开始且次数 0 | 默认为清单/规划来源；不赋予理解、应用、验证、resume_ready |
| 增加 staging 与 canonical 的展示边界 | 统一 CSV 同时包含 official、aggregate、supplement 和旧 review 标签 | staging 明确“历史/未确认”；客户端不以旧 `evidence_accepted` 冒充 Core 审核 |
| Excel 保留为证据/投影，不依赖缓存当 truth | manifest 有 11 workbook 路径/6 unique hashes；主表 3985 公式中 2316 缺缓存，Staging 3985 全缺 | 保留字节版本与缺失状态；无缓存不补零，有缓存不自动视为已重算 |
| PRD 本地目录说明与代码对齐 | AppPaths 与旧 PRD 示例数据库名不同 | 说明实际 resolve 规则与 override；不重命名用户数据库、不执行迁移 |

上述多数建议是把既有不变量落到数据呈现，不能绕过 [archive contract](../migration/ARCHIVE_REHEARSAL_CONTRACT.md) 对额外结构化映射的测试要求。需要新增 shared semantics 的条目应先由 Lead 冻结契约，worker 不自行定义。

## 4. 支持与未验证的产品假设

- 市场材料确实提供岗位文本、技能与问题出现的候选输入，但不证明推荐有效、市场代表性或投资收益。
- 多源重复、等级变化和映射差异支持 evidence/provenance/versioning 的必要性，不证明任何一个目录天然 canonical。
- 个人清单缺少实践日期与笔记，不能验证 Personal Capability、Resume truth 或面试 readiness。
- 本次市场面经没有验证用户 Application→Interview→Outcome 转化，不能据此宣布 PRD §32 四个真实反馈闭环全部完成。
- 代码测试、synthetic offline acceptance、UI 状态测试与真实业务闭环是不同验收层；实现文档应分别标注。

## 5. v1.5 编写前仍需回填的事实

1. Lead 的真实 archive/index/disposable import/reimport/backup/restore 验收及其精确 digest；成功前保持未验证。
2. Excel 的只读 sheet/公式/cache 计数已补入数据基线，仍缺公式依赖、逐项业务规则和占位确认；CSV 行数和缓存存在性不推断工作簿权威或完整性。
3. 35 URL、82 mapping 差异、source grade 变换的 reconciliation，及用户决定 canonical authority 的记录。
4. 完整 provenance 闭合与类型化结构映射测试，明确仅归档、候选、已接受三种边界。
5. Feishu schema/export 和外部写入状态分别记录；新 UI/服务集成后更新实现矩阵，不提前写成 DONE。

本文是可审查的现状修正与候选 delta。它不修改 PRD v1.4、不执行 schema migration、不选择用户身份/优先级，不合并 main、不推送，也不授权生产操作。
