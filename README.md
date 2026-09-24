# 观复 · Agent Career Harness

![观复桌面工作台预览](assets/readme/guanfu-today.png)

求职资料常散落在岗位网页、项目文件、简历和沟通记录里，改过什么、依据是什么、下一步是否确认，往往很难追溯。观复把求职机会、项目证据、能力、简历版本和沟通草稿放进一个本地优先的桌面工作台，让每次重要修改都有来源、版本和人工确认记录。

## 核心能力

- **岗位机会：** 搜索和浏览职位名称、公司、地点、来源与技能标签；由你决定是否加入求职流程。
- **项目与证据：** 将项目材料、经历和能力线索关联起来；岗位要求不会被当作个人经历事实。
- **简历审核：** 导入 TXT、Markdown 或 PDF 后先预览；逐条接受、拒绝或手动编辑建议，再生成独立简历版本，不覆盖基础简历。
- **AI 工作台：** 结合当前岗位、简历、申请和已确认记忆整理建议与沟通草稿；内容先进入待确认队列。
- **求职沟通邮箱：** 手动测试连接、读取指定文件夹并关联邮件摘要；审核后的单封草稿可交给系统邮件客户端处理。
- **历史与知识：** 追踪岗位、证据、Patch、简历版本和申请之间的稳定 ID。

## 离线 Demo 与职位数据

Windows Beta 内置 `legacy-jobs-v2` 职位种子，共 **492 条规范化岗位记录**。全部记录包含职位名称、公司、地点、岗位链接、来源类别和技能标签；其中 385 条有采集时间，263 条有发布日期。当前种子没有可验证的岗位摘要、结构化要求、薪资或工作方式值，因此它是历史岗位元数据，不是实时职位订阅或完整 JD 库；缺失信息不会补造。

种子来自经只读迁移和隐私筛查的历史岗位资料。据项目维护者确认，来源台账中的记录均有再分发许可、授权或所有权依据。发布包只包含规范化岗位元数据，不含截图、网页快照、抓取原文、个人资料或运行数据库。Demo Mode 浏览这些岗位不需要 API Key 或外网连接。

## 安装 Windows Beta

当前版本为 **`v0.1.0-beta.3` 预发布版**，适用于 Windows x64。该仓库为私有仓库，请使用有访问权限的 GitHub 账号打开[私有 Release 页面](https://github.com/lsh33lxm/career_agent_harness/releases/tag/v0.1.0-beta.3)，下载并运行 [NSIS 安装程序](https://github.com/lsh33lxm/career_agent_harness/releases/download/v0.1.0-beta.3/Agent-Career-Harness_0.1.0_x64-setup.exe)。同时下载 [SHA256SUMS.txt](https://github.com/lsh33lxm/career_agent_harness/releases/download/v0.1.0-beta.3/SHA256SUMS.txt) 校验安装包，并查看[职位数据清单](https://github.com/lsh33lxm/career_agent_harness/releases/download/v0.1.0-beta.3/manifest.json)。

首次启动可直接浏览离线 Demo 职位。Beta 是预发布版本，不是稳定版；本地浏览和记录不会自动投递岗位、自动发送邮件或执行后台批量外部操作。简历修改、申请状态和每封沟通草稿都由你审核和确认。

## 隐私、数据与验收状态

- 默认数据保存在本机；Demo 浏览不连接外部模型或平台。连接外部模型或邮箱需要你主动配置并触发。
- 职位种子只发布已筛查的规范化元数据。职位来源证据不等于个人经历或技能证据。
- **当前源码的 Desktop Verification Gate v0.1 浏览器验收：GO**（2026-09-24，生产前端与隔离 Demo API 的 Resume Review 流程及 3 项 Playwright E2E 通过，测试进程正常退出）。`v0.1.0-beta.3` 安装包没有因本次验收重建，因此此结果不代表该安装包经过了同一轮复验；Beta 仍是预发布版本。

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
