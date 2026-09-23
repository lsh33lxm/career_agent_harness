# Legacy Agent Radar 结构化导入报告

状态：**可逆历史投影已完成；canonical cutover 未执行**

演练日期：2026-09-21
Legacy 根目录：`D:\\0.小红书投稿\\小红书稿\\9.15 三期\\agent_rader`（全程只读）

## 导入边界

结构化 importer 读取现有清单中的岗位/JD、面试事件、问题明细、来源台账、个人刷题记录、
国内/海外 normalized JSONL，以及 9.16 候选平台、Official JD、Canonical Job Posting 数据。
每个源文件记录相对路径、SHA-256、原始 mtime、Artifact Store 引用、导入批次与逐行转换结果。

历史岗位进入 `job_staging_record`，保留 `job_staging_provenance`；面试、问题、来源和个人编码
记录进入 immutable `legacy_projection_record`。两者都只是历史/未确认投影。只有用户点击
“加入求职流程”时，既有 Opportunity admission 服务才会创建 canonical Job/Opportunity。
Importer 不创建个人 Fact、Capability、Resume Fact 或 Outcome。

## 干净预览数据库演练

预览 Data Root：`%TEMP%\\ach-legacy-preview-20260921-214952`。该目录与正式 Data Root 分离。

| 指标 | 结果 |
| --- | ---: |
| 读取源记录 | 7,575 |
| 岗位 staging | 1,028 |
| 历史非岗位投影 | 6,547 |
| 重复/待复核 | 684 |
| 失败 | 0 |
| 外键错误 | 0 |

在同一干净预览数据库上再次执行 importer：读取 7,575、新增 0、更新 0、未变化 7,575、
重复 684、失败 0。第二次输出证明当前映射幂等；不确定重复项保留为 `duplicate` /
`needs_review`，没有静默覆盖或丢弃。

18 条只有 OfficialJD 门户元数据、没有具体职位/JD 的记录保留为 `source` 历史投影，
没有伪造成岗位。导入前后 Legacy 文件 metadata signature 一致，源目录未被修改。

## 可见化与查询验收

桌面“机会”页默认读取历史岗位，无需输入内部 ID；支持岗位/公司/技能搜索，公司、地点与
状态筛选。详情展示公司、岗位、地点、薪资、JD、标签、关联面试，以及源文件、行号、
SHA-256 和导入批次。浏览器已在真实预览库验证 `Python` 搜索与“Agent Harness 工程师”
详情，来源定位到具体文件与行号。

API：

- `GET /api/v1/legacy/status`
- `POST /api/v1/legacy/import`
- `GET /api/v1/legacy/jobs`
- `GET /api/v1/legacy/jobs/{staging_id}`

CLI：`python -m importers.agent_radar structured-import`

## 验证

- Backend focused：`16 passed`；full regression：`652 passed, 5 skipped`
- Frontend：`18 test files, 55 passed`
- Frontend production build：通过
- Ruff（所有新增/修改 Python 文件）：通过
- Alembic：`0022 → 0023 → 0022 → 0023` 通过
- `git diff --check`：通过

## 未执行事项

没有执行正式 Data Root cutover、canonical authority promotion、Legacy 写入、外部网络写入、
main merge 或 push。A/B/C/D/S 等旧权威等级、个人身份映射与冲突 Job identity 仍受
`CANONICAL_CUTOVER_GATE.md` 约束。
