# Agent Career Harness 数据基线 v1.0

日期：2026-09-21。类型：真实 legacy 数据的只读审计 companion，不是 canonical 导入批准。
实现观察基点：`cee9162`；归档边界：shared contract `0.17.0` / D-027。

本文支持 PRD 的数据建模与验收设计，不修改 v1.4 产品原文。**行数不是业务实体去重数，归档不是事实确认，市场资料不是个人经历。** 本文未声称 archive、disposable import、backup/restore 或 canonical cutover 成功；这些步骤由 Lead 另行记录。Excel 部分引用 Lead 提供的只读结构/缓存审计，不用 CSV 推断工作簿全部内容。

## 1. 审计锚点与方法

所有下述 source 路径均相对于只读 legacy 根 `agent_rader/`，不是新仓库文件。每条路径的精确字节 hash、大小、mtime 由同一冻结清单绑定：

```text
inventory: integration/runtime/legacy-20260921/inventory.json（Git ignored）
SHA-256: 0958a30658003fd67efdce7722b1870a4c9963744e1a21f1693961b289dc43ce
files: 2426
bytes: 377785991
source metadata signature:
1f105e51963c59b11b4624679ded718ae267c509dda64480298c35d1e929cd19
```

全清单计数来自 Lead 的 fresh inventory/verify 检查点；本文内容审计选择其中 **53 份 JSON、JSONL、CSV**，覆盖 normalized、shared、`work/clean` 与统一 CSV。每次读取调用 `inventory.read_source_bytes`，绑定清单 size、mtime、SHA-256；每轮完整 source metadata signature 前后相同。未执行 legacy 脚本，未读凭据/config/session，未写 Legacy、生产库或用户文档。

JSONL 按非空记录行解析，CSV 按 header 后记录解析，JSON 数组按元素计数。对象容器另列内部数组计数，不能把一个 JSON 对象视作一个业务记录。全文仅保留字段与汇总，不包含个人文本、原始 URL 或原始记录。

可复核的 ignored 审计产物位于同一 integration `runtime/legacy-20260921/`：

- `audit-schema.json`：53 文件 schema、类型、空值、ID cardinality、占位关键词计数。
- `audit-mapping.json`：嵌套数组、literal classes、关联校验、个人数据汇总。
- `audit-conflicts.json`：稳定 ID / URL 交叉比较及变更字段计数。
- `audit-dates.json`：字段级日期范围与缺失/精度计数。
- `workbook-audit.json`：Lead 只读副本审计的 sheet、公式与缓存计数；本文不复制其示例单元格内容。
- `STRUCTURED_MAPPING_AUDIT.md`：审计摘要。

这些产物只证明本次观察。后续重跑若清单 hash 改变，应生成新的数据基线，不能沿用旧数字。

## 2. 数据集与记录口径

下表每个 source 均由 §1 的同一 manifest hash 锚定。`CN`、`overseas` 是旧数据分区，不代表市场抽样覆盖完整。

| 数据类别 | `data/` normalized | `codex/data/` normalized | 统一 CSV |
| --- | --- | --- | --- |
| 市场面经记录 | `cn/normalized/interview_events.jsonl`：248 | `cn/normalized/interviews.jsonl`：7；overseas 同名文件：0 | `data/统一数据/面试事件数据.csv`：255 |
| 问题出现记录 | `cn/normalized/question_occurrences.jsonl`：2371 | CN 同名文件：74；overseas：0 | `data/统一数据/问题明细.csv`：2445 |
| 编码题出现记录 | `cn/normalized/coding_occurrences.jsonl`：54 | CN 同名文件：3；overseas：0 | `data/统一数据/手撕题明细.csv`：57 |
| 岗位/JD记录 | `cn/normalized/jd_events.jsonl`：35；`overseas/normalized/overseas_jd_events.jsonl`：72（岗位族聚合） | `cn/normalized/job_postings.jsonl`：227；overseas 同名文件：158 | `data/统一数据/岗位与JD数据.csv`：492 |
| 来源登记 | `cn/normalized/source_artifacts.jsonl`：283 | `cn/normalized/sources.jsonl`：444；overseas 同名文件：159 | `data/统一数据/来源总台账.csv`：886 |

表中 normalized 列的路径须加该列根前缀。统一 CSV 数量与两个包的分类行数相加一致，但没有证明语义去重或唯一来源权威。

**492 不是独立 Job 数。** 同一 CSV 的 `source_classification` 为：官方 Evidence 385、官方聚合 Evidence 72、非官方补充 35。`review_status` 为 `evidence_accepted` 350、`normalized` 70、`aggregate_only` 72；均是 legacy 标签，不能当成新 Core 的批准记录。72 条海外聚合记录的 `frequency_unit` 全为 `distinct role family`，其中 `content_scanned=true` 18、false 54。不能把 `posting_count`、`title_example` 当作独立职位快照或完整要求。

其他可供后续候选映射的种子：`codex/data/shared/topics.jsonl` 30、`skills.jsonl` 27、`canonical_questions.jsonl` 19、`canonical_problems.jsonl` 271；`data/cn/normalized/canonical_questions.jsonl` 56。它们的命名空间和目的不同，不可直接合成一个“官方能力节点数”。

### work/clean 容器与候选

| source | 记录语义与数量 |
| --- | --- |
| `work/clean/interviews.json` | 231 个市场面经对象 |
| `work/clean/questions.json` | 2250 个问题对象 |
| `work/clean/coding_evidence.json` | 51 个编码题对象 |
| `work/clean/b5_new_candidates.json` | `interviews` 9、`questions` 33、`coding` 6；另有 search_log 6、failures 4 |
| `work/clean/b6_jd_candidates.json` | `verified_jds` 15、`leads` 10；另有 search_log 14、failures 5 |
| `work/clean/review_queue.json` | 42 个待审对象 |

`verified_jds` 是旧字段名，不是本文重新验证官网、职位仍开放或 Core authority 的结论。`work/clean/stats.json` 是聚合结果对象，不是独立市场事件表；不能将统计表与原始事件相加。

## 3. 已复现的重复与冲突

| 检查 | 精确观察 | 对映射的影响 |
| --- | --- | --- |
| `data/cn/normalized/jd_events.jsonl` 的 `url` 对 `codex/data/cn/normalized/job_postings.jsonl` 的 `original_url` | 35 条全部有相同 literal URL；等级配对全为 S→C | 不能算成 70 个唯一 Job，也不能按目录选权威；URL 相同尚不证明版本内容相同 |
| `work/clean/interviews.json.interview_id` 对 `data/cn/normalized/interview_events.jsonl.event_id` | 231 条 ID 全部对应；source_quality→evidence_grade 为 A→A 171、B→A 29、C→C 16、D→C 15 | 保留原始等级，核实转换规则；不可因归一化自动提升权威 |
| `data/cn/normalized/new_question_occurrences.jsonl` 对主 `question_occurrences.jsonl` | 121 个 occurrence_id 全部已有；82 条仅 canonical_question_id 不同，39 条完整记录等价 | 增量不能重复 append；映射版本变化不能按相同 ID 静默覆盖 |
| `new_interview_events.jsonl` / `new_coding_occurrences.jsonl` 对相应主文件 | 17 / 3 条均为完整记录子集 | 不能另计新增业务记录 |
| `data/cn/normalized/` 与 `data/overseas/normalized/` 中被检的 12 文件，对 `data/snapshots/2026-09-15/` 对应路径 | 12 对文件 SHA-256 全相同 | 可以去重字节，仍应保留每个原始路径和快照关联 |

上述比较见 `audit-conflicts.json` / `audit-mapping.json`，不等同于所有数据包的完整语义 reconciliation。

已验证的有限引用完整性：codex CN 227 + overseas 158 个 `job.source_id` 均在各自来源表中存在；data 的 248 个面经 `source_artifact_ids` 引用均在该包来源表中存在。**未由此证明**网页内容已保存、截图可读、全部 occurrence / provenance edge 引用闭合，或链接今日仍可访问。

## 4. 日期覆盖与缺失

来源为 §1 清单下列字段的实际聚合。只接受开头为有效 `YYYY-MM-DD`、后接结束/空格/`T` 的值，按日取 min/max；不补月/年级精度，不做时区转换。表中“其他”表示非日级格式或不符合该解析规则，不一律判为坏数据。

| source / 字段 | 总行 | 日级有效 | 空值 | 其他 | 日级范围 |
| --- | ---: | ---: | ---: | ---: | --- |
| `data/cn/normalized/interview_events.jsonl` / published_at | 248 | 226 | 22 | 0 | 2024-01-17 ～ 2026-09-05 |
| 同文件 / interview_date | 248 | 31 | 213 | 4 | 2024-08-29 ～ 2026-08-25 |
| 同文件 / effective_event_date | 248 | 222 | 22 | 4 | 2024-01-17 ～ 2026-09-05 |
| 同文件 / collected_at | 248 | 248 | 0 | 0 | 2026-09-15 |
| `data/cn/normalized/jd_events.jsonl` / published_at | 35 | 0 | 35 | 0 | 未知 |
| 同文件 / effective_event_date | 35 | 35 | 0 | 0 | 2026-09-15 |
| 同文件 / collected_at | 35 | 35 | 0 | 0 | 2026-09-16 |
| `data/overseas/normalized/overseas_jd_events.jsonl` / latest_updated | 72 | 72 | 0 | 0 | 2026-06-15 ～ 2026-09-15 |
| `codex/data/cn/normalized/job_postings.jsonl` / job_posted_at | 227 | 105 | 122 | 0 | 2025-02-05 ～ 2026-09-14 |
| 同文件 / first_seen_at | 227 | 227 | 0 | 0 | 2026-09-15 ～ 2026-09-16 |
| `codex/data/overseas/normalized/job_postings.jsonl` / job_posted_at | 158 | 158 | 0 | 0 | 2025-03-28 ～ 2026-09-14 |
| 同文件 / first_seen_at | 158 | 158 | 0 | 0 | 2026-09-16 |

采集日、首次发现日、更新日、发布日期和实际面试日不能互换。数据 CN JD 发布日全空而 effective_event_date 全为固定日期，尤其不能据此声称这些岗位都在该日发布。本文不将跨年样本概括为“最近一个月市场”。

## 5. 来源等级与个人 lane

`data/统一数据/来源总台账.csv` 的 literal evidence_grade：A 224、C 277、S 385；lane：Evidence 609、Discovery 277。旧方案仅提 A/B/C/D 不足以覆盖真实 S 级。`evidence_accepted`、A、S、`frequency_eligible` 均不是 Core `FactAuthority`、用户审核事件或个人掌握认证，映射必须记录原等级及其定义。

`data/统一数据/个人刷题记录.csv` 有 **270 行**，`刷题状态` 全为“未开始”，`做题次数` 全为 0；`上次练习`、`下次复习`、`核心思路`、`卡点 / 错误`、`解题笔记` 均为空。`Byte Hot48` 标记“是”26、“否”244。这证明存在个人练习清单，不证明做过、理解、应用或可面试讲解。旧方案提到的“另外 22 个占位”没有由本 CSV 审计验证，不能制造额外题目；相关工作簿逐项业务口径仍待核验。

关键词占位检测只用于 triage：`data/cn/normalized/coding_occurrences.jsonl` 有 7 行、`question_occurrences.jsonl` 有 1 行包含占位/待确认等标记。它可能来自题目文本，不能据此直接排除或改写记录。

### Excel 版本与公式缓存补充

Lead 的 `workbook-audit.json` 检查了 **6 个 unique hash 的只读工作簿副本**；manifest 对应 **11 个 workbook 路径**。下表每组列代表路径，重复路径仍由 manifest 保留。原始 legacy hash 经验证，未保存修改原工作簿，也未执行 Excel 重算。

| 代表 source 路径 | SHA-256 | 同 hash 路径数 | sheets | 公式单元格 | 缺缓存 |
| --- | --- | ---: | ---: | ---: | ---: |
| `Agent_Radar_研究工作台.xlsx` | `599be34cbd65155d85b6df05582412c47887cd72b4d2f253356f4d8a312326e7` | 1 | 46 | 3985 | 2316 |
| `Agent_Radar_研究工作台_Staging.xlsx` | `29c020ef690cb9b6ca33d375be2d106cde63634ad4fe0cbb2e81d5a96430b6a9` | 1 | 46 | 3985 | 3985 |
| `data/snapshots/2026-09-15/Agent_Radar_研究工作台_snapshot.xlsx` | `3a86899cf8a3f562e57e87cfcd0c6380e97690e7fe0dd0fa708ab5902efc14a3` | 4 | 35 | 3985 | 3985 |
| `work/backup/Agent_Radar_pre_migration.xlsx` | `6e3024f85acc89330431c092e44a7f01144106a544fe468bfba7b3d648cd9879` | 1 | 26 | 3985 | 3985 |
| `references/字节高频48与LeetCode-Book88刷题追踪表.xlsx` | `d2ca13f02de4238c6e04fccd0bbc55aede441114c9cf4e1aff36fa8d1ae5bbad` | 2 | 7 | 75 | 0 |
| `references/算法刷题追踪表_可视化优化版.xlsx` | `d3bda27495c39db81253c6636ccbbc082d35e390954d15a6b2a1ddb237ce9a39` | 2 | 8 | 3715 | 2062 |

主表和 Staging 都有 46 sheets，但 hash 与缓存状态不同。无缓存不表示业务值为零，有缓存也不证明已按当前输入重算。本文不把缓存统计迁入 Core，也不以 sheet 数/文件名/最后版本推定 authority；公式依赖与业务口径仍需专门验收。

## 6. 可映射对象与必须保留的边界

| 目标 | 当前证据支持什么 | 尚缺什么 / 禁止自动产生什么 |
| --- | --- | --- |
| Artifact / Source / SourceSnapshot / EvidenceRef | 精确文件字节、来源路径、包内行 selector 可支持归档 provenance | 遵循 [归档契约](../migration/ARCHIVE_REHEARSAL_CONTRACT.md)；URL 登记不等于网页字节已归档；本文不验收归档 |
| JobRevision | codex job_postings 有 source_id、外部岗位 ID、职责/要求、时间字段 | 先解决身份/版本冲突，定义记录内容 hash、row EvidenceRef、observed_at；不是直接批量 canonical |
| JobRequirement PROPOSED | 来源中的 requirements/preferred 可供候选抽取 | exact JobRef、scope、extractor、provenance 必须测试；skill 字符串不能自动接受为官方能力映射 |
| 市场面经/问题/编码观察 | 可以保留历史市场证据与提取候选 | 不是个人 Interview appointment、Application、Outcome 或 Career Fact |
| Capability 候选 / MarketBinding | topic/skill 提供候选线索 | Official Graph release、capability identity、BROAD/TARGET 边界需显式；频率不能自动生成 binding |
| PersonalCapabilityState / EvidenceBinding | 个人清单可作规划或来源证据 | 缺 candidate/capability 映射、exact revision 与用户/rule authority；270 行不能设为 mastered |
| SuggestedPriority / UserPriority / InvestmentState | 旧频次表可用作探索材料 | 旧排名不等于用户优先级或新规则结果，不从电子表格直接导入业务 truth |

## 7. 对 PRD 假设的支持、偏差与缺口

| PRD 假设 | 本基线支持程度 | 实际含义 |
| --- | --- | --- |
| §2.2 Evidence-constrained；§10 官方与个人分层 | 支持其必要性 | 等级漂移、聚合与明细混合、未开始个人清单说明不能共享一个 truth 标签 |
| §6/§15 岗位要求与 Match/Gap | 有候选输入，尚未验证效果 | 有结构化职责/技能，但缺已批准能力映射、个体条件与结果对照，不能证明匹配有效 |
| §12 能力初始化与增量更新 | 有种子且需要版本管理 | 多套 canonical questions、82 个映射差异说明必须保留版本；不能验证官方图谱完整性 |
| §13/§16 个人状态与项目证据 | 本次不足 | 练习清单没有完成证据；未审计个人项目实现与 contribution，不能断言 mastery |
| §14 投资建议 | 尚未验证收益 | 频次不是投入回报，未建立受控用户行动/结果评估 |
| §32 四个反馈闭环 | 不构成真实闭环验收 | 市场面经不是用户投递/面试结果；未由本基线取得真实 Application→Outcome 转化证据 |

偏差包括非随机采集、公开分享者偏差、来源包重复、历史窗口混合、缺失实际面试日期、官网聚合未逐页扫描、CN/overseas 数据结构与覆盖不对称。不能把 source 数当独立受访人数、把 topic 出现率当招聘总体需求率，或把旧榜单当当前优先级。

未决项：来源等级定义与变换政策、35 URL 身份/版本冲突、82 question mapping 版本选择、完整 provenance closure、credential/混合容器分类、Excel 公式/占位/版本族、归档与恢复验收、结构化映射测试、canonical authority 选择。本文只冻结观察，未替用户决定权威，也未把完成代码测试等同于真实数据验收。
