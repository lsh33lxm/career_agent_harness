# Agent Career Harness 当前状态

## 2026-09-25 安装窗口官方来源状态验收探针

- `scripts/probe_installed_window.mjs` 现在先在真实安装 WebView 中打开机会页，使用本地拦截的官方来源响应形状 fixture 点击“读取官方岗位”，验证岗位标题、待核验数量、连续失败次数和最近错误，再继续 Resume Review 与原生窗口关闭流程。
- 该探针验证安装版 UI 与来源生命周期投影的连接，不宣称线上来源在安装验收中可访问；线上来源结论仍以官方现场审计为准。
- 本轮前端生产构建和 Node 脚本语法检查通过；包含新探针的 NSIS 安装包尚待重建，旧安装包不作为本轮证据。

## 2026-09-25 官方来源状态生产浏览器验收

- 新增 Playwright 生产构建用例，使用本地官方来源响应形状 fixture 验证岗位搜索结果、来源健康状态、待核验数量、连续失败次数和最近错误均可见。
- 用例通过：`official source panel renders lifecycle health and staged provenance`（1 passed）；使用本机缓存 Chromium，外部请求被拦截，截图保存在本地 `artifacts/verification/`，不进入 GitHub。
- 该证据验证桌面 UI 与既有生命周期 API 的连接，不替代官方站点现场数据验证；腾讯完整 JD 仍为当前唯一已现场验证的完整 JD 来源。

## 2026-09-25 官方来源状态与失效追踪桌面投影

- 官方来源面板现在读取既有 `listing-lifecycle` 与 `source-policies` 投影，展示来源启用状态、连续失败次数、最近错误，以及岗位观察的有效/待核验/已失效数量和最近检查时间。
- 读取失败只显示中文非阻塞提示，不改变岗位搜索、准入或 JD 审核状态机；失效判定仍由后端完整成功快照规则控制。
- 前端 `OfficialSourcesPanel` 专项测试 4 项通过，桌面生产构建通过；后端岗位雷达与生命周期回归 17 项通过。
- 2026-09-25 只读来源复核：阿里校园入口返回模板页，百度校园页超时，华为入口 TLS 失败，小米候选地址 404；字节校园页约 816 KB 仍未提取到稳定岗位记录。未接入猜测 API，也未宣称第二个完整 JD 来源。

## 2026-09-25 当前提交安装版 Resume Review 与来源回归

- 当前提交重建 Windows sidecar 与 NSIS 安装包；Cargo check、桌面生产构建通过。安装包 SHA-256：`227ca724c0f0baf5f0384ad13bd31b509b8b0509743525e28e1f87b34b734a72`；sidecar SHA-256：`c7c5b63c62ef79d42288154cc2f3555305b2e61226b4a852173f359f5d6f8c26`。
- 在新安装目录与隔离数据目录完成真实安装窗口 Resume Review：接受、拒绝、手动编辑后接受、生成 ResumeRevision、两张截图、原生窗口关闭及 Playwright 清理；安装退出码 0、桌面退出码 0、sidecar 数量 0，结果 `passed`。
- 本地证据目录：`artifacts/verification/installed-runtime-capability-20250925/evidence/`；截图均为 `1860x1200`，不纳入 Git。
- 官方来源、Job Radar 与 JD 要求后端专项回归：17 项通过。美图详情路由仍未证实；字节跳动官方页面可达并含职位描述字段，但列表/详情接口尚未定位，不接入猜测接口。
- 2026-09-25 对字节跳动校园站两个公开查询 URL 做响应形状复核：响应约 816 KB，未提取到稳定岗位标题、岗位 ID 或详情链接；命中的 `id` 均为站点字段配置/元数据 ID，不能当作岗位记录。

## 2026-09-25 官方 JD 审核能力映射闭环

- 官方来源面板读取现有个人能力档案与当前能力图谱，只展示 active 能力节点。
- 每条 proposed JD 要求现在必须由用户选择能力映射后才能接受；提交同时携带 `capability_id` 与 `graph_version_id`，拒绝仍可直接操作。
- 新增回归覆盖“选择 Python 能力后接受候选要求”；官方来源面板专项测试 3 项通过，桌面端生产构建通过。
- 能力档案读取失败提示改为非阻塞状态提示，避免与页面主错误状态冲突；前端全量回归 30 个测试文件、84 项通过。

## 2026-09-25 `.ics` DTSTAMP 修正

- 面试事件的 `DTSTAMP` 现在使用本次导出时间，`DTSTART`/`DTEND` 继续使用预约时间并转为 UTC；避免把未来预约时间误当事件生成时间。
- 日历与申请页专项测试 5 项通过，桌面端生产构建通过。

## 2026-09-24 面试日历导出

- 申请页新增“导出 .ics”，复用现有面试记录与状态，不改变申请或面试状态机。
- 导出遵循 RFC 5545：稳定 `UID:<interview_id>@career-agent-harness`、UTC 起止时间、取消状态、申请与面试稳定 ID；事件按面试时间排序。
- `calendar.test.ts` 与 `ApplicationsPage.test.tsx` 共 5 项通过，桌面端生产构建通过。

## 2026-09-24 已安装 Windows 窗口 Resume Review 验收

- 为主窗口 capability 增加最小 `core:window:allow-close` 权限，修复安装版通过 WebView2 调用窗口关闭时的 ACL 拒绝；未扩大 shell、文件或网络权限。
- 使用新构建的 NSIS 安装包，在独立安装目录和 `ACH_DATA_DIR` 中启动真实 `http://tauri.localhost/` 窗口；脚本 `scripts/verify_installed_window.ps1` 调用 `scripts/probe_installed_window.mjs` 完成接受、拒绝、手动编辑、生成 ResumeRevision，并保存两张安装窗口截图。
- 证据目录：`artifacts/verification/installed-runtime-aclclose-20260924-final2/installed-window-e2e/`；截图均为 `1860x1200`。`installed-window-summary.json` 记录桌面退出码 `0`、sidecar 数量 `0`、CDP 端口进入 `TIME_WAIT`，结果为 `passed`。
- 与源码浏览器子门、全新安装 492 条离线种子、端口恢复和 sidecar 生命周期证据合并后，**Desktop Verification Gate v0.1：GO（当前源码验证范围）**。仍不创建稳定版，不启用自动投递、自动发信或后台批量操作。

## 2026-09-24 当前 HEAD Windows 回归与安装验证

- 当前源提交：`a23863bd9dc07df6cbe25fc145d181b4923c8c01`（包含腾讯官方详情 API、官方来源面板和 JD 修改后审核）。
- 浏览器子门：`scripts/verify_desktop_gate.ps1` 通过，3 个 Playwright 用例全部通过，证据目录为 `artifacts/verification/desktop-gate-20260924-221259/`，包含流程截图、重启持久化和 teardown 结果。
- 当前 HEAD sidecar 已重建，SHA-256：`bcde0ee96f64e8a04b07054dcb3baacbfec74607a3a9e049f49256478099833d`；NSIS 安装包已重建，SHA-256：`764f321eda53135754d31f5d1dd2f5c4486f81bffb33aa6430d3d57deed6cc16`。
- 全新安装验证目录：`artifacts/verification/installed-runtime-head-20260924-221910/`。安装退出码 0；被占用端口 `57281` 后恢复到 `56677`；`/health=200`，环境为 `demo`；离线 packaged seed 返回 492 条；应用退出码 0，未留下本轮桌面端或 sidecar 进程。
- 全量后端 `747 passed, 5 skipped`；前端 `29 个测试文件 / 79 passed`；Cargo check 通过。5 项跳过均为 Windows symlink 创建权限限制。Ruff 全仓仍有 22 个既有格式/行长问题，未将其混入本轮改动。
- 整体 Desktop Verification Gate 仍不改判为 GO：当前已有源构建浏览器证据和安装生命周期证据，但尚未在安装后桌面窗口中完成同一套真实 Resume Review 点击链路；不得据此创建新的 prerelease。
- 本轮尝试使用 Windows Computer Use 连接已安装窗口；`cua.getState()` 返回 `apps=[]` 并报 `unsupported Codex auth method: apikey`，因此没有产生安装后窗口的点击或截图证据。该连接问题不能由 API/命令行验证替代。

## 2026-09-24 美图官方 SSR 岗位列表适配

- `campus.meitu.com` 现场页面为 Next.js SSR，公开 `initJobList` 当前解析出 190 条岗位，其中校园招聘/实习生招聘 77 条；适配器仅保留这两类，社会招聘不混入。
- 每条保留职位 ID、标题、部门、地点、站点标识、公开发布日期和稳定详情 URL（`/jobCampus/{id}` 或 `/jobIntern/{id}`）；未知字段不补造。
- 详情路由现场返回“岗位信息不存在”，因此完整 JD 尚未宣称已验证；当前来源可用于真实列表发现，详情待站点接口可公开读取后再接入。
- 新增 SSR 字段变化、类型过滤和关键词查询回归测试；专项测试 8 项通过，Ruff 通过。

## 2026-09-24 腾讯官方岗位 API 与完整 JD 适配

- 现场确认 `join.qq.com` 的公开只读接口：`POST /api/v1/position/searchPosition` 返回真实岗位列表，`GET /api/v1/jobDetails/getJobDetailsByPostId?postId=...` 返回完整职责、任职要求、地点和岗位元数据。
- 适配器已接入现有 Job Radar 暂存流程，限制分页、请求体和官方域名；详情必须精确匹配 `postId`，不会把首页或其他岗位当成详情。现场关键词 `AI` 返回 526 条记录，首条详情包含 6 条任职要求。
- 增加本地关键词过滤，避免官方接口宽松匹配导致无关岗位混入；未知字段保持为空，不提交表单、不读取 Cookie。
- 腾讯官方来源专项测试 10 项通过，Ruff 通过；美图详情仍未验证完整 JD。
- 新增 `POST /api/v1/jobs/official-detail` 与桌面端“查看完整官方 JD”入口；详情沿用来源白名单、稳定官方 URL、完整原始响应和规范化要求，不改变岗位准入或审核状态机。API/适配器专项回归 14 项通过，官方来源面板测试 2 项通过，桌面生产构建通过。
- JD 候选逐条审核支持“修改后接受/拒绝”：审核命令创建不可变的新 requirement revision，保留原文版本、Evidence 引用和审核理由；桌面端提供候选文本编辑框。要求 API/服务测试 8 项、官方来源面板测试 2 项通过，未新增数据库表或迁移。
- 美图官方主页仍可现场读取校园/实习列表；截至本次检查，公开详情路由/API 未形成可验证的完整 JD 返回，继续保持“列表已验证、详情未验证”，不将其作为腾讯之外的完整 JD 来源。

## 2026-09-24 Desktop Verification Gate 浏览器子门复验

- 运行 `powershell -ExecutionPolicy Bypass -File .\scripts\verify_desktop_gate.ps1` 成功，生产前端构建通过。
- 3 个 Playwright 用例全部通过：Resume Review 逐条接受/拒绝/手动编辑并生成 ResumeRevision；API 重启后 History/Knowledge 保留稳定 ID；API 不可用时 Demo Mode 保持可用并显示中文恢复提示。
- 本次证据目录：`artifacts/verification/desktop-gate-20260924-145756/`；`run-summary.json` 为 `result=passed`，生成完整流程截图和独立 Playwright 输出，脚本 finally 正常清理自己启动的 API/Vite 进程。
- 本次验证确认浏览器子门已通过，但尚未在本次源码提交上重新安装 NSIS 包。因此整体 Desktop Verification Gate 继续为 **NO-GO**，剩余门槛是 NSIS 全新安装、492 条职位离线加载、sidecar 退出和端口恢复复验。

## 2026-09-24 Desktop Verification Gate v0.1 全链路复验

- 使用当前源码重建 sidecar：SHA-256 `ec2ec57f3e73f4b493a620221397b0aee0be498e5943d6a1678cff876207feb3`；Tauri NSIS 构建成功。
- 全新安装目录：`artifacts/verification/installed-runtime-current-20260924/install`；独立数据目录：`artifacts/verification/installed-runtime-current-20260924/data`。
- 安装后首次启动自动完成迁移，sidecar 在 30 秒内 ready，`GET /health` 返回 200；离线 `POST /api/v1/jobs/packaged-seed-search` 返回 492 条，与 manifest/种子一致。
- 使用已占用测试端口启动时，应用放弃冲突端口并在新的回环端口 `51908` ready；关闭本轮桌面进程后，本次安装对应 sidecar 和端口均已释放。旧验证目录中的历史进程未被本轮停止。
- 安装包 SHA-256：以 `artifacts/verification/tauri-target-20260924-current/release/bundle/nsis/Agent Career Harness_0.1.0_x64-setup.exe` 为准，验证摘要保存在 `artifacts/verification/installed-runtime-current-20260924/`。
- 浏览器子门与安装门均通过，**Desktop Verification Gate v0.1：GO（本次源码验证范围）**。仍禁止自动投递、自动发信和正式稳定版发布。

## 2026-09-24 Beta.4 预发布

- 从源码文档提交 `bd5327f` 生成干净快照分支 `snapshot-desktop-gate-full-20260924`，最终快照提交 `034371529f64c90da23a84e15dff7f912e2676be`；仅保留根 `README.md`，没有 `docs/`、参考仓库、运行数据库、日志或缓存。
- GitHub 预发布：`v0.1.0-beta.4`，地址：<https://github.com/lsh33lxm/career_agent_harness/releases/tag/v0.1.0-beta.4>。
- 已上传 Windows NSIS 安装包、`SHA256SUMS.txt` 和 `manifest.json`。安装包 SHA-256：`5c40a3bf730a9fcf508cef02462a4d351d3324bc305dd8e817ac3780b042201f`。
- 预发布说明明确 492 条 `legacy-jobs-v2` 数据、离线 Demo Mode、人工确认边界和 Desktop Verification Gate v0.1 为 GO；没有创建正式稳定版。

## 2026-09-24 官方国内校招来源适配器首个切片

- 新增腾讯校招 `join.qq.com` 与美图校招 `campus.meitu.com` 两个只读官方来源适配器，统一接入现有 Job Radar 暂存、去重、公开来源 Evidence 和用户准入流程。
- 适配器限制官方域名白名单、12 秒超时、2 MB 响应上限和最多 3 个详情链接；不读取 Cookie、不提交表单、不绕过验证码或反检测机制。
- 支持 JSON-LD `JobPosting` 的职位名称、公司、地点、类型、发布日期、更新时间、完整描述和来源 URL；未知字段保持为空。响应内容由现有 Evidence artifact SHA-256 留存。
- 专项测试 `tests/unit/test_official_job_sources.py` 5 项通过；Job Radar API 与现有 fixture 回归 7 项通过；项目范围 Ruff 通过。
- 现场只读检查（2026-09-24）：腾讯和美图主页 HTTPS 均可达，但当前页面返回前端壳，未发现可解析 `JobPosting`，现场岗位数量均为 0。该结果标记为“来源可达、线上岗位解析未验证”，不能作为真实岗位抓取成功证据；完整链路由保存的官方页面形状 fixture 验证。
- 当前新增入口为 `POST /api/v1/jobs/official-search`，支持来源 ID、关键词、偏好地点和岗位筛选参数。后续需要针对站点实际搜索 API 或岗位详情路由补充分页快照、完整 JD 现场验收与失效追踪。
- 机会页已接入“国内官方校招来源”面板：可选择腾讯/美图、输入关键词、查看暂存岗位的完整描述要求、来源 SHA-256 和官方链接；结果不会绕过现有用户准入动作。
- 前端专项测试 1 项和 `npm --workspace @ach/desktop run build` 通过。

## 2026-09-24 JD 候选要求审核 API

- 新增岗位要求 API：按精确 Job revision 列出最新候选、创建带 Evidence 引用的 `proposed` 要求，并以用户命令逐条接受/拒绝/标记 superseded。
- 审核写入沿用现有 `JobService` 与不可变 requirement revision；错误的并发 revision、缺失岗位版本、空理由和未经正式能力图映射的接受请求均 fail loud。
- 集成测试 `tests/integration/test_job_requirements_api.py` 2 项通过；覆盖提议、列出、拒绝和接受缺少能力映射的安全拒绝；相关 Ruff 通过。
- 当前仍缺岗位详情中的逐条 UI（下一切片）以及从官方完整 JD 章节提取候选；当前官方页面现场未提供可解析岗位，fixture 不能冒充线上 JD。
- 许可审计：本地 `reference-repos` 中 CareerDesk、JobHuntBot 为 MIT；Magic Resume 仓库同时附加“仅个人非商业使用”的限制条款，不能把其代码直接嵌入公开仓库。用户点名的 `offer-harvester`、`Campus-Jobs-Scraper`、`JobHunter` 当前不在本地参考目录，本轮未复制其代码或资源。

## 2026-09-24 官方来源岗位的 JD 逐条审核桌面链路

- 官方来源面板现在支持用户点击“加入并审核 JD”：先调用现有 staging admission，再按岗位 Evidence 和稳定 ID 幂等创建候选要求。
- 每条候选要求显示原文文本和状态，用户可逐条拒绝或接受；拒绝保留审核理由，接受继续由后端要求正式能力映射，不能绕过领域状态机。
- 前端专项测试通过，`npm run build`（`apps/desktop`）通过。当前官方站点现场仍返回前端壳、未解析出线上岗位，因此该链路由保存的 fixture 和后端集成测试验证，不能冒充线上抓取成功。
- 新增 `GET /api/v1/jobs/staging/{staging_id}/source-document`，从内容寻址 Evidence artifact 读取完整原始岗位响应，返回来源 URL、抓取时间和 SHA-256；fixture 回归验证原文与暂存哈希一致。快照只读，不写回旧来源。

## 2026-09-24 申请看板与面试日历读取切片

- 新增 `/applications` 桌面页，复用现有 `/api/v1/applications` 和 `/api/v1/applications/{id}/interviews` 读模型，按 Career Core 申请状态分列展示，并按本机时区排序已安排面试。
- 页面不创建第二套状态机；当前为只读投影，申请状态转移、本人确认投递、面试安排/改期/取消写操作仍需通过现有 `ApplicationService` 与 `InterviewService` 命令 API 接入。
- 页面专项测试 1 项和桌面生产构建通过。
- 新增受用户命令保护的 Application/Interview API：创建申请、准备状态切换、绑定 ResumeRevision、本人确认投递、合法状态推进，以及安排/完成/取消面试；所有命令要求精确 revision 并固定 `actor=user`。API 集成测试 1 项通过，未提交申请安排面试会被拒绝。
- 机会页新增“创建准备中申请”用户动作，调用上述 API 后跳转提示到申请看板；不会自动投递或发送消息。申请页专项测试和机会页回归共 4 项通过，生产构建通过。
- 申请看板卡片新增 ResumeRevision 选择与关联、进入待本人确认、本人确认投递控件；每次写入携带当前 Application revision，提交后只记录用户确认，不访问外部 ATS。页面测试通过，生产构建通过。
- 已投递/面试中的申请卡片新增轮次、时间和“安排面试”控件，写入现有 Interview 服务并同步本地日历列表；不自动通知、不自动推进申请状态。页面测试和生产构建通过。

## 2026-09-24 Desktop Verification Gate v0.1 浏览器验收 — NO-GO

- 当前源码生产构建上的真实 Chromium Resume Review 流程通过：逐 Patch 接受、拒绝、手动编辑、生成 ResumeRevision；基础简历保持不变，Application 保持 `preparing`；历史和知识页能追溯稳定 ID。
- API 重启持久化、API 不可用时 Demo 浏览与中文恢复提示均通过；首屏在 30 秒内显示，浏览器没有外网请求。
- Playwright：3 项 E2E 全部通过；runner 正常退出。脚本确认初始 API、重启 API 与生产预览进程均已退出，动态端口已释放。
- 12 张全页/多视口/恢复状态截图保存在 `artifacts/verification/desktop-gate-20260924-090053/`；本次独立数据目录在验收后回收。
- 验收脚本现在先构建前端并使用生产预览，Playwright runner 文件位于独立 `playwright-output/`，不会清理运行数据或日志。修复 Demo API 岗位 ID 不匹配时详情空白，以及 E2E 的旧区域名/模糊按钮定位。
- 验证：桌面全量组件测试 `27 files / 76 passed`；`npm --workspace @ach/desktop run build` 通过；本地 `git diff --check` 对本轮文件通过。
- GO 范围是当前源码生产前端与隔离 Demo API 的浏览器验收。`v0.1.0-beta.3` NSIS 安装包没有因本次修复重建，未创建新 Release，也没有 GitHub 写入。

## 2026-09-24 492 条职位种子安装强验证

- 当前 NSIS 安装包 SHA-256：`EC8D4BFCCEFE49344B6062D585E7DB9D8AE8E62D132214451A53B1777BFCA6BC`。
- 全新安装目录和独立 `ACH_DATA_DIR`：`artifacts/verification/installed-runtime-job-seed-20260924-strong`。
- Demo sidecar 在动态回环端口 `65528` 启动，`GET /health` 返回 `200`，环境为 `demo`。
- 安装后离线 `POST /api/v1/jobs/packaged-seed-search` 返回 `492` 条；本地种子文件和 manifest 均为 `492` 条，SHA-256 为 `2f99952eb8103a5b420261d04e1365517581cd928ddaa61b5598818a2402c7a3`。
- 日志未出现旧 `agent_rader` 路径；关闭窗口后应用退出码为 `0`，无匹配残留进程。证据写入该验证目录的 `verification.json`、`shutdown.json` 和 `data/logs/desktop-sidecar.log`。
- 该结果满足 492 条离线种子加载门槛；真实 Resume Review 浏览器逐步点击、完整截图和 Playwright teardown 仍未完成，Desktop Verification Gate 继续为 **NO-GO**。

## 2026-09-24 求职沟通邮箱安全切片

- 新增 IMAP 账户配置、连接测试、指定文件夹手动读取和邮件摘要关联岗位/Application。
- 密码只通过 SecretStore 保存；数据库和 API 响应只保存 `credential_ref`，不记录密码、邮件原文或附件。
- 读取使用 IMAP readonly 模式，单次最多 50 封；连接和读取异常转换为中文安全提示。
- 专项后端测试、前端邮箱页面测试和生产构建通过；仍不自动轮询、自动发信或批量发送。

## 2026-09-24 Beta.3 发布验证

- 邮箱集成提交：`61c39c2`；runtime 装配修复：`fd2bf44`。
- 完整后端回归：`728 passed, 5 skipped`；前端：`27` 个测试文件、`75` 项通过；Ruff、生产构建、Cargo check 通过。
- 修复后的 NSIS 安装包 SHA-256：`1787B9C4FFC6C2FB6F949740D6CE96B834F24EDA13F8BF1C254443B987189229`。
- 全新安装 Demo 验证：`/health=200`、离线 packaged seed `492` 条、无旧路径、退出码 `0`、无残留进程。
- 私有 prerelease：`v0.1.0-beta.3`；快照提交：`4a3b24b6bf55efbcf9f244a17b1682b4364d1285`，分支 `beta-snapshot-mailbox-20260924`。
- Desktop Verification Gate 仍为 **NO-GO**：真实 Resume Review 浏览器点击链路、完整截图和 Playwright teardown 尚未完成。

## 2026-09-23 legacy job release eligibility update

- 用户确认本批数据为公开、非商业可使用数据，并批准以公开 URL、平台/来源类型和官方来源标记作为再分发依据。
- 迁移脚本新增显式 `--attest-source-ledger-authorization` 政策开关；未显式启用时仍保持保守的 `local-only` 分类。
- 用户确认来源台账整体具有再分发许可、授权或所有权依据；真实重跑读取 492 条岗位和 886 条来源台账：`release-eligible=492`、`local-only=0`、`excluded=0`。
- 生成 `data/jobs/jobs.json`（492 条，SHA-256 `2f99952eb8103a5b420261d04e1365517581cd928ddaa61b5598818a2402c7a3`）和更新后的 `data/jobs/manifest.json`；原始 `agent_rader` 保持只读。
- 该结果允许进入种子数据/安装验证，但仍需完成全量测试、干净安装和安全快照检查后，才能评估私有 Beta。
- 已接入现有 Opportunity Radar：`PackagedJobSeedSource` 通过 `/api/v1/jobs/packaged-seed-search` 读取安装资源，复用 staging、评分、用户 admission、Evidence 与 Resume Review 链路，不依赖 `agent_rader`。
- 真实加载验证需按新 manifest 重跑；此前后端回归 `725 passed, 5 skipped`，前端 `25 files / 73 tests`，生产构建和项目范围 Ruff 通过。
- 当前源码 sidecar 重建成功（SHA-256 `70653fc4bbc7c2a7506b1c1a6b8e3389db6771565b65f36ecbafeb873bcb7354`），Tauri NSIS 构建成功；安装包仅保留在本地验证目录，未提交或发布。
- 本轮尚未完成全新安装后的岗位页面可视检查、Resume Review 浏览器逐步点击截图和 Playwright teardown；因此 Desktop Verification Gate 仍为 **NO-GO**，Beta prerelease 不创建。
- 修复 PyInstaller 资源路径和 `null` requirements 兼容后，旧种子干净 NSIS 安装实测 `/health=200`、离线种子查询返回 350 条，sidecar 正常退出；492 条新种子需要重新构建安装包验证。
- `v0.1.0-beta.1` 快照在最后两项安装修复提交前已生成，不能作为最终一致性发布；将以包含 `_MEIPASS` 资源路径和 `null` requirements 修复的下一 beta 重新发布。

## Private beta publication (2026-09-24)

- Repository visibility was corrected from public to private through the authorized GitHub API operation.
- Clean snapshot source: `c91557b`; snapshot commit: `6dcf2a571f26bbd240545740e18c8892fee76f4c` on branch `beta-snapshot-20260924`.
- `v0.1.0-beta.1` prerelease created with NSIS installer, `SHA256SUMS.txt`, and `manifest.json` assets. Installer SHA-256: `9c9cf1867960e2991399b36cdbf6b7a8cfe35a69e7450f27b8a7c9a31018710b`.
- Release snapshot verifier passed: 515 files, only `README.md` Markdown, no docs, generated caches, secrets, or raw legacy data; manifest count/SHA matched 350 records.
- Existing remote `main` history was preserved; the clean snapshot was pushed as `beta-snapshot-20260924` because replacing remote `main` would require a prohibited force/history rewrite.

## RecruitOps audit (2026-09-24)

- 固定参考 commit：`5715c59cf976c995a79ca23bf37cea1f1ef3a0a9`；根许可证 MIT。
- 已证实的代码能力（静态路径与测试文件可定位）：FastAPI API、岗位发现/规范化、简历解析与匹配、Application 记录、招聘邮件读取/草稿预览、AI 助理和 Playwright 浏览器适配器。
- 当前环境公开测试尝试：`uv run --project . --extra dev pytest -c pytest-public.ini` 依赖安装完成，但 Python 启动阶段因仓库包元数据 GBK 解码错误退出；Docker/Postgres、Playwright 浏览器和真实邮箱未运行，因此这些外部依赖功能标为 `unverified`。
- 许可结论：根代码可按 MIT 借鉴；`packages/desktop_filler/NOTICE` 明确无原始许可证且不授予再分发权，禁止复制其引擎/资源。观复只采用行为边界和现有自有实现，不复制受限资源。

## AI workbench increment (2026-09-24)

- 新增上下文感知的 AI 工作台，绑定岗位、基础简历、Application 和已确认记忆，并在界面显示稳定 ID。
- 当前生成逻辑为本地规则建议；保存结果只进入 `pending_review` 沟通草稿队列，provenance 保留岗位、简历和 Application 引用。
- 不覆盖基础简历、不改变 Application 状态、不自动投递、不自动发信；后续模型接入仍必须沿用待确认边界。
- 新增专项测试通过；前端全量测试在默认文件并行下曾出现共享 `fetch`/模块 mock 污染，单文件和串行全量均通过。`vite.config.ts` 已关闭文件级并行以保持确定性。
- 最新前端全量结果：25 个测试文件、73 个测试全部通过；生产构建通过。Desktop Verification Gate 仍为 **NO-GO**。

## Resume import and communication mailbox increment (2026-09-24)

- 新增简历导入面板：本地 TXT/Markdown/PDF 经过现有本机解析接口生成提取预览，用户明确确认后才创建新的 ResumeBase；不覆盖已有基础简历。
- 新增“求职沟通邮箱”页面：读取本地沟通草稿、逐封填写审核理由并批准/拒绝；批准后只打开系统邮件客户端草稿，不调用发送接口，不保存邮箱密码、不后台读取邮箱、不批量发送。
- 新增专项测试 2 项通过，生产构建通过；前端全量回归与新 NSIS 包仍需在本切片提交后重跑。Desktop Verification Gate 继续 **NO-GO**。

## 2026-09-23 数据迁移门

- 在 `feature/legacy-job-data-migration` worktree 中完成只读 Agent Radar 岗位审计脚本 `scripts/migrate_legacy_jobs.py`。
- 实际读取 492 条岗位记录和 886 条来源台账记录；输入 SHA-256 已写入 `data/jobs/manifest.json`，审计摘要写入 `data/jobs/migration-report.json`。
- 用户确认来源台账授权后，分类为 `release-eligible=492`、`local-only=0`、`excluded=0`；492 条规范化种子已生成。
- 脚本支持 `ACH_LEGACY_AGENT_RADAR_DIR`、`--expected-jobs-sha256`、`--allow-public-source-noncommercial`、幂等重跑和源哈希变化失败；迁移单测通过 4 项。
- Beta 安装、GitHub prerelease、RecruitOps 审计与功能增量仍需通过后续构建、安全和许可检查；Desktop Verification Gate v0.1 仍为 **NO-GO**。

更新时间：2026-09-23；集成分支：`integration/ui-desktop-release-v0.1`；代码已本地集成到 `main`（`b746730`）。Desktop Verification Gate v0.1 仍为 **NO-GO**。

## Desktop Verification Gate v0.1（2026-09-23）

- 已新增本地 Playwright E2E 配置和隔离运行脚本 `scripts/verify_desktop_gate.ps1`；脚本动态分配端口、使用任务专属 `artifacts/verification/desktop-gate-<timestamp>` 数据目录、请求拦截外网，并只清理其创建的进程树。因当前 Windows Playwright test runner 挂在 teardown，完整 UI 用例未取得通过结果或截图；Playwright 1.63 对应 Chromium 1243 下载遇到 Google Storage 30 秒超时，本机缓存 Chromium 1234 可由直接 Playwright API 启动，但 runner 仍未完成。
- 修复 sidecar 启动参数：通过参数显式传递非敏感 environment/host/port/origin；launch token 仍只作为子进程环境变量。端口探测现在会识别连接成功但不返回 API 响应的占用者并更换端口。
- 本轮最终自动回归：`.venv/Scripts/python.exe -m pytest -q` 为 `720 passed, 5 skipped`；`.venv/Scripts/ruff.exe check backend tests migrations scripts` 通过；`npm test -- --run` 为 24 个测试文件、71 项通过；`npm run build`、`cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml` 与 `git diff --check` 通过。`npm run lint` 未定义；按要求的 `ruff check .` 会遍历只读参考仓库，报告其 2,368 条既有问题，已改用项目源码目录 lint。
- Windows 发布构建通过：使用独立 `CARGO_TARGET_DIR=artifacts/verification/tauri-target-20260923`，运行 `npm --workspace @ach/desktop exec -- tauri build`，生成 NSIS 安装包。为构建使用当前源码 sidecar，旧的仓库 sidecar 在构建结束后按 SHA-256 原样恢复（前后均为 `692fd89ab87bd7c1936f3af50febee39d0a9a6c6002ab2c9f16fd05e479fe8091`）。
- 干净隔离安装启动通过：安装至忽略目录 `artifacts/verification/clean-install-v3`，设置 `ACH_DESKTOP_DEMO=1`、`ACH_DATA_DIR=artifacts/verification/desktop-runtime-smoke-v3`；主窗口标题“观复职业工作台”，sidecar 端口 `54145` 健康，34 个 migration 完成，前端发出本地 `/health`、Today、Knowledge 请求。关闭窗口后 App/sidecar 退出。
- 端口冲突恢复通过：本轮监听器占用 `46282`；sidecar 日志记录 `loopback port 46282 is occupied by a non-API service`，随后切换 `51643` 并记录 `local API ready`。窗口关闭后 App/sidecar 进程均退出。发布 exe PE subsystem 为 `2`（Windows GUI，无 console subsystem）。
- 失败侧车诊断曾通过真实安装启动复现：旧构建 sidecar 不支持当前 demo token 规则，日志保留 traceback、退出码和 readiness failure，UI 窗口继续显示；随后已以源码 sidecar 重建并完成成功启动。旧 sidecar 文件没有被最终覆盖。
- 截图尚未生成；Demo 岗位/Patch/Revision/Application 本轮新 UI 链路 ID 尚未产生。后端此前已验收记录仍是岗位 `opportunity_4a0d1f026edd89e3e11afe3694be250a`、Patch `patch_cbbabb4065401b997538e9ea` / `patch_e75651e1963b3a36df4167c0` / `patch_4493228e40647df83ac75e1a`、Revision `resume_revision_demo_target_83a14d40fb26dd09ecf0c151`、Application `application_fbdd11d28d86432cb74ee48a`，本轮没有将其冒充为桌面验收结果。
- 当前 Gate：**NO-GO**（缺真实浏览器逐步交互截图、浏览器 runner teardown 阻塞和页面断 API/失败状态截图）。桌面安装启动、无控制台子系统、sidecar ready/退出及端口占用恢复已实测通过。

## 桌面与 UI 集成收口（2026-09-23）

- 本地 Git 集成：`refactor/v1.4-integration` 提交 `af64c99240b8c3bd5afd20533f369e05223d5f68`；UI 分支 `ui/cohesive-desktop-redesign` 提交 `0bf59524cd2872e180622c0b9192a61bf568e6a0`；合并验证提交 `b74673028e3799a516874331522a70d64c7a6ed8`。`main` 已由非快进合并更新。
- 集成 worktree 全量验证：Python `720 passed, 5 skipped`；前端 24 个测试文件、72 项通过；项目范围 Ruff、`npm run build`、Tauri `cargo check`、`git diff --check` 通过。5 项跳过原因是 Windows symlink 权限。
- 本地 Chromium 可视 smoke：随机空闲端口 `62987`；Demo visual-review fixture + 本地 mock API；截图 `artifacts/verification/ui-smoke-20260923-221418/`，10 页 × 1536/1440/1280 三种宽度共 30 张，标题均可读且未检测到横向溢出。此 smoke 不是 Resume Review Gate 的真实逐 Patch 点击验收。
- Playwright 完整 Resume Review 用户链路仍受 Windows runner teardown / 浏览器下载限制阻塞，未产生完整链路截图；无浏览器工作流稳定记录 ID。Desktop Verification Gate v0.1 继续为 **NO-GO**。
- UI 收口中统一保留 `ProviderMark` 和 `CompanyAvatar` 本地组件、模型厂商预设与逐页视觉布局；参考图不进入运行时资产。冲突解决保留 sidecar 与中文启动错误提示，并把 Demo Story 稳定 ID 链接纳入新布局。
- 主项目原有 7,490 个未跟踪文件（约 336 MB）与合并路径无重叠；临时 stash 后恢复，未清理这些本地文件。集成未跟踪运行物与截图保持在 Git 忽略目录，原始 `agent_rader` 未写入。

## 当前结论

- v2.0 Slice A–E（Plugin Foundation、Career Knowledge、Resume Studio、Opportunity Radar、Lifecycle / Replacement）：**DONE for local/offline scope**。
- Career Core 与 Capability Visualization：**DONE**，真实读模型、evidence provenance 与用户 authority 边界保持。
- Plugin Marketplace：manifest/schema、scoped runtime、生命周期、scan/quarantine、审计、更新策略、卸载影响与桌面页面已实现；第三方执行仍隔离。
- Legacy inventory/archive/rehearsal/backup restore：**DONE for reversible subset**；2,426 files、2,205 preserved、17 deferred。
- Legacy structured projection：**DONE for historical/unconfirmed scope**；真实演练读取 7,575 条，形成 1,028 条岗位 staging 与 6,547 条历史投影；重复 684、失败 0，未执行 canonical cutover。
- Evidence provenance、History、Feishu offline projection：**DONE / offline only**。
- 历史岗位与面试关联已可查询；legacy authority → canonical Job/Fact/Capability 映射仍为 **NEEDS USER AUTHORITY**。
- Feishu external write：**BLOCKED_EXTERNAL_ACTION**（credentials、destination permission、sync contract）。
- 中文桌面工作台第二阶段：**DONE for current routes**。Project、Resume 与 Capability 入口改为列表、搜索和选择，不再要求用户在首屏填写内部 ID；导航、错误、空状态和当前内置工具目录已中文化。
- 中文展示收口：**DONE for current routes**。能力、证据、历史、插件、Today、资料源、任务、项目与简历页面不再把内部 authority、stage、renderer、review、sync、source kind 或市场信号枚举直接展示给用户；技术名词（如 GitHub、HTML、ATS、SHA-256）按产品边界保留。
- 模型服务配置：**IMPLEMENTED, CONNECTION UNVERIFIED WITHOUT USER CREDENTIALS**。OpenAI、Anthropic、DeepSeek 与 OpenAI-compatible 的非敏感配置进入 Core DB，密钥只进入 Windows Credential Manager；只有真实 `/models` 测试成功才显示“已连接”。受控 CLI Runner 仍未实现。
- GitHub 项目分析：**IMPLEMENTED / LIVE FETCH BLOCKED BY NETWORK**。只读有界 clone、静态档案、Project 关联、私有 token 安全存储与 UI 已完成；合成仓库链路通过。当前机器访问 `github.com:443` 失败，未伪造真实公开仓库验收结果。
- Windows 桌面交付：**IMPLEMENTED / CLEAN-INSTALL ACCEPTANCE PASSED**。Tauri 2 自动管理 PyInstaller sidecar、随机 loopback 端口与每次启动临时令牌；令牌不进入命令行或日志，退出时回收完整进程树。NSIS 安装包已生成并在全新安装目录/数据目录完成首次启动、建库、重启持久化与 sidecar 日志验收。
- 真实知识投影：**IMPLEMENTED**。知识页默认展示 Legacy 只读导入形成的 1,028 条岗位、503 条面试、4,816 条问题、324 条刷题记录及来源路径/SHA-256/行号；Today 在 Core 队列为空时显示真实历史岗位入口，但不自动加入求职流程或改变用户优先级。

## 最新验证

- Resume Review Gate v0.1（本地 Demo only）：逐 Patch 接受、拒绝和手动编辑写入 Career Core 审核修订与事件；仅用户确认的 Patch 形成独立 ResumeRevision 快照，基础简历不覆盖；preparing Application 精确引用版本。Story、历史与知识读模型保留岗位、Requirement proposal、Evidence、审核、版本和申请的稳定 ID；Demo API 要求显式隔离 `ACH_DATA_DIR`。
- Resume Review Gate 独立 HTTP/重启验收：`ACH_DATA_DIR=%TEMP%/ach-resume-review-gate-20260923`；岗位 `opportunity_4a0d1f026edd89e3e11afe3694be250a`，Patch `patch_cbbabb4065401b997538e9ea`（手动编辑后接受）、`patch_e75651e1963b3a36df4167c0`（接受）、`patch_4493228e40647df83ac75e1a`（拒绝），Revision `resume_revision_demo_target_83a14d40fb26dd09ecf0c151`，Application `application_fbdd11d28d86432cb74ee48a`。API 进程重启后 Story 与 Application 仍读取同一版本和审核决定；基础简历保持不变，申请状态为 `preparing`。
- 当前工作树最终验证：`.venv/Scripts/python.exe -m pytest -q` 通过 `720 passed, 5 skipped`；5 项因 Windows symlink 创建权限跳过。`npm test -- --run` 为 24 个测试文件、71 项通过；`npm run build`（含 `tsc -b`）通过；`.venv/Scripts/ruff.exe check backend tests migrations scripts` 与 `git diff --check` 通过。仓库没有 `npm run lint` 脚本。系统 Python 裸跑因未安装项目依赖导致 collection error，不属于有效回归；项目虚拟环境完整回归通过。
- 本地运行检查：Vite `http://127.0.0.1:5183` HTTP 200；隔离 Demo API `http://127.0.0.1:8783/health` HTTP 200 且 `environment=demo`。CUA 浏览器通道报 `unsupported Codex auth method: apikey`，本轮没有浏览器截图或可视点击证据；不将 HTTP 检查视为可视验收。
- 原始 legacy CSV 本轮只读指纹复核与此前记录相同：SHA-256 `477ed75bb81dd2a66a1b06f91c8af5bfb5997704b6a0c4d0d7bf19b9482eef60cd`；原始 `agent_rader` 工作区未写入。
- 历史回归基线（更早提交）：Backend `715 passed, 5 skipped`；Frontend `23 test files, 67 passed`，不代表当前工作树计数。
- Knowledge/Today focused：backend `2 passed`；frontend `7 passed`；真实 overview API 返回岗位 1,028、面试 503、问题 4,816、刷题 324、待复核 709。
- Legacy preview：读取 7,575、新增 0、更新 0、未变化 7,575、重复 684、失败 0；FK errors 0，源 metadata signature 不变。
- Clean-install migration：首轮读取 7,575、新增 7,575、重复 684、失败 0；第二轮新增 0、未变化 7,575，导入前后源签名一致；`Python` 查询返回 10 条并抽样核对源文件、SHA-256、行号、批次与 JD。默认 `%LOCALAPPDATA%\AgentCareerHarness` 也已完成一次同样的幂等导入，岗位 staging 1,028、历史投影 6,547、失败 0。
- Desktop packaging：PyInstaller one-file smoke、Cargo check、Vite production build、Tauri debug no-bundle 与 release NSIS bundle 均通过；隔离安装版首次建库后监听随机端口，窗口关闭后 sidecar 进程数归零。
- v2.0 hardening focused：backend `32 passed`、Plugins UI `1 passed`；Ruff `backend tests migrations` 与 `git diff --check` 通过。

## 下一阶段与授权依赖

1. 修复 CUA 浏览器认证并完成 Resume Review Gate 可视端到端验收；随后复验 Tauri Windows 安装、sidecar 生命周期、端口冲突和退出清理。本地 HTTP、组件测试与生产构建不能替代这一步。
2. 真实 marketplace、WeKnora、crawler/portal、Typst compiler 与 external-write adapters 仍需 credentials、license/terms/security 核验和明确授权。
3. 按 CANONICAL_CUTOVER_GATE 决定 source identity/authority/mapping，再实施结构化 Core 导入；当前只保存历史 evidence。

禁止 main merge、push、生产 Feishu 写入、canonical cutover、legacy 修改和破坏性迁移。

详见 [v2.4 当前实现与下一阶段 PRD](docs/prd/ACH_v2.4_PRD_当前实现与下一阶段.md)。

## G1 离线求职闭环

- G3 简历导出：**PARTIAL**。ResumeRevision JSON/Markdown 导出、ResumeData 校验、文本/PDF fallback 导入预览、可注入 OCR adapter 边界、用户确认后的 ResumeBase 保存、基础版本历史查看、旧版本追加式恢复、服务端 undo/redo、按需差异查看和本地草稿 undo/redo 已实现；当前环境没有 OCR 引擎，图片 OCR 实际解析仍待补齐。
- G4 面试成长：**PARTIAL**。文本会话事件、面试复盘 proposal、规则化 STAR 结构与内容具体性信号、独立学习计划 proposal、批准后进入有界任务队列、批准后的 Memory consolidation 任务入队，以及历史页可触发的 Offer 准备/拒信模式分析 proposal 已实现；更丰富的模型化评分和跨会话编排仍待补齐。
- G5 知识治理：**PARTIAL**。Memory 来源亲和度与 consolidation proposal、Wiki health 检查与知识页 review-gated 修复建议、SourceConnector schedule metadata、有界运行、单次 scheduler enqueue tick、认证 MCP transport boundary、JSON-RPC stdio 适配器、有界 SSE 事件适配器和 CLI 命令白名单/危险参数拒绝已实现；真实网络监听/生产认证、常驻 dispatcher 和宿主级 sandbox 隔离仍待补齐。

- G2 沟通草稿：**PARTIAL / proposal-only**。机会页支持本地保存、查看、批准或拒绝草稿；每日限额、按渠道统计、回复与待跟进摘要已可读，不会执行真实发送。

- 新增 `/api/v1/career-loop/offline`：离线岗位 fixture → 可解释评分 → 用户 admission → Resume TargetProfile → EvidenceRef-backed 简历提案 → 观复主题 PDF/ATS 报告。
- 提案不会自动批准或提交申请；闭环集成测试、Ruff 和 diff check 已通过。

## 历史完成记录（只作审计，不代表当前计数）


- Confirmed the new repository path.
- Read the authoritative PRD v1.2 in full.
- Confirmed the new repository initially contained only the PRD.
- Confirmed the legacy Agent Radar workspace is outside this repository and is not
  a Git repository.
- Confirmed 38 source Project Cards exist in the read-only records directory.
- Confirmed local Node, npm, Python, Rust, and Cargo toolchains are available.
- Established security exclusions, architecture/migration documents, proposed
  ADR-013 through ADR-016, and research indexes.
- Added authenticated localhost-only FastAPI `/health` endpoint.
- Added Alembic/SQLite fresh bootstrap with current state, immutable revision,
  DomainEvent, idempotency, transactional outbox, and migration mismatch tables.
- Added typed Evidence/ExtractedClaim/Fact, Command/revision, 11 Core module
  boundaries, LocalStepRunner contract, and content-addressed Artifact Store.
- Verified atomic command commit and idempotent replay behavior.
- Backend verification: Ruff passed; pytest passed 14 tests on Python 3.13.12.
- Added React/TypeScript/Vite App Shell with Today, Discover, Opportunities, Resume,
  Applications, Interviews, Prep, Insights, Evidence, and Settings routes.
- Added typed bearer-authenticated frontend health client, loading/offline states,
  error boundary, responsive navigation, and disabled future controls.
- Fixed authenticated CORS preflight handling after real browser integration found
  that `OPTIONS /health` was incorrectly rejected.
- Added a minimal Tauri 2 shell and restrictive default capability/CSP boundary.
- Frontend verification: Vitest passed 4 tests, Vite production build passed, npm
  audit found 0 vulnerabilities, and browser verification displayed `Core 0.1.0`.
- Added a read-only Agent Radar importer with no-link traversal, streaming SHA-256,
  workbook structural metadata, output-boundary guards, and post-scan verification.
- Added typed candidate manifest and reconciliation schemas. Identity mappings remain
  null, approved entities remain empty, and conflict dispositions default explicitly
  to `deferred`.
- Real legacy inventory verified 2,210 files (360,355,195 bytes), 286 snapshot
  candidates, and 11 workbooks without observed source metadata changes. Generated
  reconciliation contains 332 deferred candidate records.
- Added OS-aware application data paths that keep ordinary artifacts, backups,
  browser sessions, and logs separate.
- Added a redacting SecretProvider boundary backed by environment injection; no
  secret values are persisted or logged.
- Added consistent SQLite online backup, artifact manifest/hash verification,
  integrity check, non-overwriting restore, and a full restore rehearsal test.
- Added typed Candidate, Market, Opportunity, Resume, Application, Interview, Prep,
  Outcome, Approval, Run, and Snapshot skeletons plus a repository protocol.
- Added executable invariants for Opportunity/Application separation,
  Prepared/Submitted separation, workflow/business state separation, user-only final
  approval, and TEST-to-PROD rejection.
- Generated the standard Tauri icon set from a deterministic project SVG, resolved
  Rust dependencies into `Cargo.lock`, passed `cargo check --locked`, and built the
  Windows debug executable with `--no-bundle`.
- Integrated Capability, Opportunity, Project Evidence and Context Core contracts.
- Added typed Opportunity persistence, atomic command writes, independent priorities,
  read repository and authenticated Local API.
- Added additive Capability migration `0003` with separate official graph, candidate
  inbox, personal overlay, evidence/market binding and explainable investment records.
- Enforced immutable released graphs, authority allowlists, revision-preserving personal
  state, binding consistency and investment rule consistency at the SQLite boundary.
- Integrated the Opportunity desktop page with authenticated read/admission/priority APIs,
  Core-owned canonical ID generation, independent Suggested/User Priority projections and
  retry-safe mutation refresh behavior.
- Verified the Opportunity UI at desktop, 390 px and 320 px widths with no horizontal
  overflow or incoherent overlap; Vitest passed 16 tests and the Vite build passed.
- Added additive Project Evidence migration `0004` with revisioned scan scopes/manifests,
  immutable evidence, exact Capability evidence revisions, relational Project Capability basis
  rows and L1 enhancement tasks.
- Enforced deny-wins normalized paths, non-empty immutable manifests, evidence authority/review
  limits and atomic Project Capability aggregate writes at the SQLite boundary.
- Verified `0003 -> 0004 -> 0003 -> 0004`, Ruff, and backend `136 passed, 1 skipped`; the skip is
  the existing Windows symlink-permission limitation.
- Added additive Context Manifest migration `0005` with immutable ordered asset/knowledge refs,
  exact Project Evidence revisions, parent-last aggregate finalization and contract `0.2.0`.
- Context persistence stores only bounded audit metadata and hashes; it does not store task input,
  asset/knowledge payloads, assembled context, compiled prompts or fact-mutation authority.
- Verified `0004 -> 0005 -> 0004 -> 0005`, Ruff, and backend `151 passed, 1 skipped`.
- Added atomic Context compilation write/read integration: typed manifest, generic revision,
  `context.compiled` event and idempotency now share one transaction.
- Replay returns the first canonical manifest timestamp; compiler output is rebound to the exact
  request before persistence, and payload content cannot use generic audit rows as a storage path.
- Verified backend `159 passed, 1 skipped`, full Ruff lint, focused format and diff checks.
- Added typed Capability reads for exact/latest official graphs, candidate inbox, identity-scoped
  personal overlays, exact evidence bindings, target/broad market bindings and investment states.
- Added additive migration `0006` to reject candidate/capability identity drift across one
  `personal_state_id`; historical drift fails upgrade without rewriting data.
- Promoted exact `project_evidence_id` plus revision into the shared `EvidenceBinding` contract and
  removed the temporary repository-only read envelope.
- Added canonical Project/scope reads and a scope-safe local scanner: POSIX uses `openat`/`dir_fd`
  with no-follow handles; Windows rejects UNC/device/non-fixed drives and verifies reparse/final
  path containment while reading from the same handle.
- Independent reviews found no remaining P0/P1. Integration verification passed `192` tests with
  `3` known Windows symlink-permission skips; full Ruff passed.
- Added immutable Job revisions and versioned JobRequirements. AI/Agent proposals cannot review
  themselves; accepted requirements must pin an official capability and graph version.
- Added exact/latest Project Capability state, ordered basis and enhancement task repository reads;
  malformed aggregates fail loud and existing stable-identity triggers now have direct tests.
- Independent reviews found no P0/P1/P2 in either workstream. Combined integration verification
  passed `221` tests with `3` known Windows symlink-permission skips; full Ruff passed.
- Added immutable Evidence artifact/source/snapshot/reference persistence with exact provenance,
  credential/session rejection, typed reads and fail-loud malformed-data handling.
- Added additive migration `0008` and typed repositories for immutable Job revisions and versioned
  JobRequirements, preserving legacy Opportunity orphans while guarding future canonical refs.
- Added atomic Job/Requirement commands: typed rows, generic revision, DomainEvent and idempotency
  commit together; only USER commands can review proposals, and accepted mappings require exact
  official capability membership.
- Independent review found no P0/P1. Backend verification passed `237` tests with `3` known Windows
  symlink-permission skips; Ruff, format and diff checks passed.
- Added the pure evidence-aware Match/Gap policy over frozen exact inputs: COVERED requires both
  personal scope dimensions and qualified non-AI evidence per scope; AI_INFERRED, stale and
  unqualified evidence are excluded; Project Capability State contributes proximity only; dangling
  provenance and unreferenced inputs fail closed; output is deterministic under input reordering.
- Independent final review found no P0/P1; P2 test gaps (evidence-only coverage, rejected/superseded
  evidence, unreferenced inputs, mismatched personal state, full-input reordering) were added.
  Backend verification passed `252` tests with `3` known Windows symlink-permission skips; Ruff,
  format and diff checks passed.
- Added durable Match/Gap persistence (merge `b04d08e`): additive migration 0009 with immutable
  assessment/requirement-result/canonical-gap tables, typed reads, an atomic record service
  (typed rows + generic revision + `match.assessed` + idempotency in one transaction) and an exact
  Opportunity revision read. Independent review found one P1 (Opportunity JobRef binding) plus P2
  validation gaps; all fixed before merge. Backend verification passed `274` tests with `3` known
  Windows symlink-permission skips; Ruff and diff checks passed.
- Added the exact Match input resolver, assess orchestration and stored-manifest replay (merge
  `288ee30`): all inputs resolve through exact reads and fail loud on dangling or drifting
  provenance; replay re-runs the stored policy version against the stored manifest and never
  writes. Independent review found no P0/P1. Backend verification passed `292` tests with `3`
  known Windows symlink-permission skips; Ruff and diff checks passed.
- Linked Project Enhancement Tasks to canonical Gaps (merge `cadba69`): propose/transition
  commands validate that `target_gap_id` resolves and `target_capability_id` matches the Gap,
  with whitelist status transitions, atomic rollback and idempotent replay. Independent review
  APPROVE with no P0/P1; Lead fixed the transition generic-state shape and added transition
  idempotency coverage before merge. Backend verification passed `302` tests with `3` known
  Windows symlink-permission skips; Ruff and diff checks passed.
- Added claim review and Fact promotion (merge `d43ebe4`): additive migration 0010 with immutable
  claim/fact revision tables, typed reads, and atomic propose/review/promote commands. Review is
  USER/RULE-gated with self-review rejection; initial promotion binds fact content to the accepted
  claim. Independent review found no P0/P1. Backend verification passed `320` tests with `3` known
  Windows symlink-permission skips; Ruff and diff checks passed.
- Added Resume Core (feature `c6bfe66`, merge `df5f4d2`): additive migration 0011, USER-owned base
  revisions, exact provenance-qualified patch proposals, USER-only review, immutable content-hashed
  revisions, atomic events/idempotency and fail-loud expected-value hashes. Focused tests passed
  `7`; integration passed `327` tests with `3` known Windows symlink-permission skips.
- Added Today UI (feature `7ebd4be`, merge `989b47e`): reused the existing AppShell/router, aligned
  primary navigation, separated Suggested Priority/User Priority/Match, preserved confirmation
  gates and isolated typed fallback data pending a Core Today read model. Frontend passed `16`
  tests and production build; 1366/1920/2048 visual checks passed and forced 390 px metrics showed
  no horizontal overflow.
- Froze W2-APP contract `0.7.0` (`d61af6c`) and strengthened the existing Application/Outcome
  models (`5727af6`): Applications pin exact Opportunity revisions; submitted-or-later states
  require exact ResumeRevision/time/authority; portal receipts require Evidence refs; Outcomes are
  separate single-revision truth pinned to exact Application revisions. Full backend verification
  passed `329` tests with `3` known Windows symlink-permission skips. No migration or ATS action was
  added.
- Added additive Application/Outcome persistence and atomic services (`4b0bb68`): migration 0012
  stores immutable Application revisions and sealed Outcome Evidence aggregates; exact
  Opportunity/Resume/Application/Evidence refs fail loud; portal receipt source type is validated
  in service and write layers; submission identity cannot drift across later revisions. Focused
  tests passed `11`; full backend verification passed `332` tests with `3` known Windows
  symlink-permission skips. No ATS execution, credentials or raw form answers were added.
- Added authenticated read-only Resume/Application/Outcome projections (`83b7b91`): exact/latest
  Resume and Application reads plus Outcome history use the localhost bearer boundary; missing
  records fail with 404 and no Application write route/service is exposed. API regression passed
  `11`; full backend verification passed `334` tests with `3` known Windows symlink-permission
  skips.
- Added user-controlled interview completion, cancellation, and rescheduling commands. Rescheduling
  requires the exact current scheduled revision, preserves the Application/round/evidence binding,
  and creates `interview.rescheduled`; the desktop calendar exposes all three actions with revision
  conflict/error feedback. Focused backend verification passed `11` tests; desktop page test and
  production build passed. Desktop Verification Gate remains NO-GO pending real Windows browser
  Resume Review clicks, complete screenshots, and Playwright teardown evidence.
- Added source-compatible listing lifecycle observations: successful non-empty snapshots update
  last_seen_at; one missing item becomes pending_verification; two consecutive complete non-empty
  snapshot misses become inactive. Empty snapshots and failed or blocked collections do not advance
  missing counts. API: GET /api/v1/jobs/listing-lifecycle.
- Tightened official JSON-LD JD extraction: explicit duty sections are excluded from candidate
  requirements, while qualification sections remain eligible and unsectioned short descriptions
  stay backward compatible. Official source regression and API tests passed (8 focused tests).
- Extended Resume Studio import validation to preserve unknown top-level Magic Resume fields for
  forward-compatible round trips. Existing base revisions remain immutable and patch/review gates
  are unchanged. Resume Studio/API tests passed (7 focused backend tests plus 2 desktop tests).
