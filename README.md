# 观复 · Agent Career Harness

![观复桌面工作台预览](assets/readme/guanfu-today.png)

求职资料常散落在岗位网页、项目文件、简历和沟通记录里，改过什么、依据是什么、下一步是否确认，往往很难追溯。观复把求职机会、项目证据、能力、简历版本和沟通草稿放进一个本地优先的桌面工作台，让每次重要修改都有来源、版本和人工确认记录。

## 核心能力

- **岗位机会：** 搜索和浏览职位名称、公司、地点、来源与技能标签；由你决定是否加入求职流程。
- **官方校招来源：** 只读接入腾讯 `join.qq.com` 的公开岗位列表与完整 JD；美图 `campus.meitu.com` / `hr.meitu.com` 的校园/实习列表与公开详情页已现场验证。
- **JD 逐条审核：** 在岗位来源面板查看原文快照，逐条接受、拒绝或修改候选要求；接受时绑定已确认能力节点，保留证据和不可变修订历史。
- **项目与证据：** 将项目材料、经历和能力线索关联起来；岗位要求不会被当作个人经历事实。
- **简历审核：** 导入 TXT、Markdown 或 PDF 后先预览；逐条接受、拒绝或手动编辑建议，再生成独立简历版本，不覆盖基础简历。
- **简历工作室：** 可编辑基础简历的标量字段和结构化数组条目；编辑对象条目时保留未展示字段，并继续通过 Patch Review 和本人确认生成不可变版本。
- **AI 工作台：** 结合当前岗位、简历、申请和已确认记忆整理建议与沟通草稿；内容先进入待确认队列。
- **求职沟通邮箱：** 手动测试连接、读取指定文件夹并关联邮件摘要；审核后的单封草稿可交给系统邮件客户端处理。
- **历史与知识：** 追踪岗位、证据、Patch、简历版本和申请之间的稳定 ID。
- **面试准备与复盘：** 对已完成面试生成技术/行为准备、回答反馈和学习缺口提案；所有内容先进入 Knowledge Proposal，必须本人审核后才会进入确认流程。

## 离线 Demo 与职位数据

Windows Beta 内置 `legacy-jobs-v2` 职位种子，共 **492 条规范化岗位记录**。全部记录包含职位名称、公司、地点、岗位链接、来源类别和技能标签；其中 385 条有采集时间，263 条有发布日期。当前种子没有可验证的岗位摘要、结构化要求、薪资或工作方式值，因此它是历史岗位元数据，不是实时职位订阅或完整 JD 库；缺失信息不会补造。

种子来自经只读迁移和隐私筛查的历史岗位资料。据项目维护者确认，来源台账中的记录均有再分发许可、授权或所有权依据。发布包只包含规范化岗位元数据，不含截图、网页快照、抓取原文、个人资料或运行数据库。Demo Mode 浏览这些岗位不需要 API Key 或外网连接。

## Windows 构建状态

仓库已有 Windows 预发布版 [`v0.1.0-beta.4`](https://github.com/lsh33lxm/career_agent_harness/releases/tag/v0.1.0-beta.4)，其中包含安装包、数据 manifest 和 SHA-256 校验文件。它对应此前的干净发布快照；当前源码分支在此之后又增加了官方来源、简历工作室和面试复盘改动，因此不要把 Beta.4 当作当前源码的构建产物。

当前源码生产浏览器子门通过 3/3；同构建 NSIS 安装、隔离数据、492 条离线查询、sidecar 健康和退出也已验证。最新安装版探针在 `artifacts/verification/installed-manual-nsis-20260925/` 保存了官方来源面板、Resume Studio、申请/面试日历截图；本次真实安装版复验在 `artifacts/verification/manual-real-debug-7/` 使用 `use_fixture=false`，完成机会页导航、真实本地 sidecar `demo-start/demo-story`、Resume Review 接受/拒绝/手动编辑后接受、ResumeRevision 生成、三张完整截图和 Playwright teardown，退出码为 0、sidecar 数量为 0。基于该安装构建与验证范围，**Desktop Verification Gate v0.1：GO（本次安装构建与验证范围）**。该结论不自动延伸到未来重建包；重建安装包必须重新执行同样的验证。稳定版仍禁止，不得把本地 Demo 证据扩展为线上来源或自动投递能力。

安装版验收的关键摘要为 `installed-window-summary.json`：`desktop_exit_code=0`、`sidecar_count=0`、`result=passed`。复现需要使用全新的安装目录、独立 `ACH_DATA_DIR` 和专用 WebView2 CDP 端口：

```powershell
pwsh -File scripts/verify_installed_window.ps1 `
  -InstallRoot <安装目录> `
  -CdpPort 9245 `
  -ArtifactRoot artifacts/verification/installed-window-current
```

申请页提供按 Career Core 状态分列的申请看板、面试安排/改期/完成/取消和 RFC 5545 `.ics` 日历导出。导出的事件使用稳定面试 ID、UTC 时间和申请关联字段，便于导入本地日历。

岗位来源适配器只访问官方公开页面或接口，限制域名、分页、响应大小和请求次数；不会读取 Cookie、绕过验证码、提交表单或自动申请。来源现场验证结果和未知字段状态以代码与数据 manifest 为准。

2026-09-25 现场复核记录：美图 `AI` 查询返回 8 条岗位，前 3 条公开详情均成功读取并解析；腾讯与美图验证均为人工触发的只读请求，现场数量会随站点内容变化。

本地浏览和记录不会自动投递岗位、自动发送邮件或执行后台批量外部操作。简历修改、申请状态和每封沟通草稿都由你审核和确认。

已发布 Windows 预发布版：[`v0.1.0-beta.4`](https://github.com/lsh33lxm/career_agent_harness/releases/tag/v0.1.0-beta.4)。它对应历史发布快照，不包含当前源码的全部后续修改；当前提交也尚未作为新的安装包发布。

## 隐私、数据与验收状态

- 默认数据保存在本机；Demo 浏览不连接外部模型或平台。连接外部模型或邮箱需要你主动配置并触发。
- 职位种子只发布已筛查的规范化元数据。职位来源证据不等于个人经历或技能证据。
- **当前 Desktop Verification Gate v0.1：GO（本次安装构建与验证范围）**。`manual-real-debug-7` 已完成真实安装版机会页、真实本地 sidecar、Resume Review 三种人工决定、完整截图、原生关闭和 Playwright teardown；摘要记录 `desktop_exit_code=0`、`sidecar_count=0`、`result=passed`。未来重建包仍需重新验证；稳定版发布仍禁止，本地证据保存在 `artifacts/verification/` 且不进入 GitHub 快照。

该安装版 Gate 结论不影响离线 Demo 的使用：岗位浏览、搜索、筛选、简历草稿审核、申请看板和面试日历均可在本机运行。Gate 结论仅覆盖已记录的安装构建与验证范围，后续构建需重新验收。

## 本地开发

桌面端使用 Tauri 2、React、TypeScript 和本地 Python API。以下命令安装依赖、运行前端测试并构建生产前端：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pip install --no-deps -e .
npm ci
npm test
npm run build
```

源码浏览器子门验证：

```powershell
pwsh -File scripts/verify_desktop_gate.ps1
```

该脚本验证源码生产预览和 API 恢复路径；安装窗口验收仍需在独立临时 `ACH_DATA_DIR` 中执行，并保留本地截图和正常退出证据。
