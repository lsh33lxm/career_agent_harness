# v0.1.0 端到端验收记录

## Desktop Verification Gate v0.1（2026-09-23，部分通过）

### UI / 集成分支复核（2026-09-23）

- integration 分支 `af64c99240b8c3bd5afd20533f369e05223d5f68` 与 UI 分支 `0bf59524cd2872e180622c0b9192a61bf568e6a0` 合并至本地 `main`，最终集成提交 `b74673028e3799a516874331522a70d64c7a6ed8`。代码合并完成不改变 Desktop Gate 结论。
- 合并验证命令和结果：Python `.venv`（位于 integration worktree）`-m pytest -q`：`720 passed, 5 skipped`；`npm test -- --run`：24 files / 72 passed；项目范围 `ruff check backend tests migrations scripts`、`npm run build`、`cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml`、`git diff --check` 均通过。Cargo check 使用 integration worktree 已有 sidecar，按 SHA-256 原样复制至合并 worktree 被忽略的 sidecar 路径；该二进制没有提交。
- 浏览器 visual smoke 在 Windows 本地 Chromium 1234 完成，不依赖云端 CUA：本地 mock API、Vite 空闲端口 `62987`、查询 `?demo=visual-review`；30 张实际截图位于忽略目录 `artifacts/verification/ui-smoke-20260923-221418/`，命名 `<宽度>-<页面>.png`，宽度为 1536/1440/1280、页面为 today/opportunities/projects/capabilities/resume/history/context/settings/plugins/knowledge。标题读取成功，未发现 body 横向溢出。该 smoke 只验证页面加载和视觉布局，不执行或证明 Resume Review Gate 用户点击链路。
- 完整 Resume Review Playwright 测试仍在 Windows runner teardown 阻塞；runner 未完成真实 Patch 审核至 Revision/Application/历史/知识流程，也未生成该流程的稳定 ID 截图。Chromium Playwright 固定版本下载仍受 Google Storage 网络超时影响。Desktop Verification Gate v0.1 **NO-GO**。
- UI 冲突收口：AppShell 保留 UI 分组导航/折叠/窄屏菜单和 sidecar 中文启动错误；History/Knowledge 保留新 UI 分区并展示 Demo Story 稳定 ID；JobRadarPanel 保留 UI Surface 并保留逐条审核与 Revision 操作。测试修正 `listitem` 查询歧义，mock screenshot 脚本 Ruff 行宽已修复。
- 可视记录矩阵在 [`visual-review.md`](visual-review.md)，截图与日志证据目录被 `.gitignore` 的 `artifacts/` 规则忽略，不提交构建物或运行数据。

- 最终回归：`.venv/Scripts/python.exe -m pytest -q` = `720 passed, 5 skipped`（Windows symlink 权限）；`.venv/Scripts/ruff.exe check backend tests migrations scripts` 通过；`npm test -- --run` = 24 files / 71 passed；`npm run build`、`cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml`、`git diff --check` 通过。`npm run lint` 未定义。全仓 `ruff check .` 会进入 `reference-repos/` 第三方参考代码并报 2,368 条 lint；不作为项目代码回归。
- 浏览器执行入口：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_desktop_gate.ps1`；Playwright 用例位于 `apps/desktop/e2e/resume-review-gate.spec.ts`，截图/日志目标为 Git 忽略的 `artifacts/verification/desktop-gate-<timestamp>/`。脚本执行时 API/Vite 动态端口由临时 loopback listener 分配，Demo SQLite 位于同目录 `runtime-data`；测试结束停止自有进程树并删除该 DB 目录。
- 本轮浏览器执行未通过：Playwright 1.63 runner 在 Windows 下无浏览器测试输出并最终因 `clear output` / `apply rebaselines` teardown 120 秒超时；测试期间没有 API 业务请求，也没有生成截图。锁定 revision Chromium 1243 下载命令 `node node_modules/playwright/cli.js install chromium` 因 `https://storage.googleapis.com/chrome-for-testing-public/153.0.8010.12/win64/chrome-win64.zip` 连接 30 秒超时中止。本机缓存 Chromium 1234 的直接 Playwright API 冒烟通过，但不代表 E2E 通过。
- Windows 发布命令：`$env:CARGO_TARGET_DIR='artifacts/verification/tauri-target-20260923'; npm --workspace @ach/desktop exec -- tauri build`；结果 NSIS x64 安装包生成成功。构建使用 sidecar 源码重建，仓库现有 sidecar 文件通过 SHA-256 前后比对恢复。产物：`artifacts/verification/tauri-target-20260923/release/bundle/nsis/Agent Career Harness_0.1.0_x64-setup.exe`。
- 干净安装 Demo 运行：NSIS 静默安装到 `artifacts/verification/clean-install-v3`，启动环境 `ACH_DESKTOP_DEMO=1`、数据目录 `artifacts/verification/desktop-runtime-smoke-v3`。桌面窗口“观复职业工作台”打开；sidecar 日志 `artifacts/verification/desktop-runtime-smoke-v3/logs/desktop-sidecar.log` 显示端口 `54145` 就绪、数据库迁移至 `0034_prepared_application_resume`、API health 200 和本地 Today/Knowledge 请求。没有 API Key 或外部网络请求配置。
- 端口冲突命令场景：测试程序先用 `TcpListener` 占用 `46282`，设置 `ACH_DESKTOP_TEST_PORT=46282` 启动安装版；日志显示 occupied 错误后重启 sidecar 到 `51643`，最终 health ready。关闭本轮桌面窗口后 App/sidecar 均退出。
- 失败启动：旧 sidecar 安装版曾因 `A per-launch token is required outside tests` 退出，日志完整保留 traceback/退出码与 20 秒 readiness 失败；按源码重建 sidecar 后 Demo 干净启动通过。该失败日志位于 `artifacts/verification/desktop-runtime-smoke/logs/desktop-sidecar.log`。
- 黑窗验证：`agent-career-harness-desktop.exe` 的 PE Optional Header Subsystem 为 `2`（Windows GUI）。这证明主程序不是 console subsystem；未使用桌面截图/窗口枚举证明视觉上不存在任意外部 console 窗口。
- 本轮未产生新岗位、Patch、ResumeRevision 或 Application ID，因为完整 UI 点击链路未执行；关联 ID 只能引用本文件此前“独立本地 API + 进程重启”验收记录，不能视作桌面验收数据。
- 原始 `agent_rader` 未被本轮命令作为输入；未对其目录或 CSV 写入。NSIS 安装器、sidecar/build target 与运行日志留在 Git 忽略的 `artifacts/verification`，专属 SQLite runtime-data 在脚本 finally 中清理。

### 桌面闸门下一步

优先修复或替换 Windows Playwright runner teardown（避免对用户 Edge 使用系统 channel），随后执行完整页面点击链路和六张脱敏截图；补齐断 API 中文状态 UI 截图。之后以真实窗口自动化复验 sidecar 崩溃提示和主窗口退出清理，再将 Gate 从 NO-GO 更新。

## 已验证

- Legacy 核心岗位 CSV 只读审计：492 行，源文件 SHA-256 `477ed75bb81dd2a66a1b06f91c8af5bfb5997704b6a0c4d0d7bf19b9482eef60cd`。
- 脱敏演示生成：固定 seed `ach-demo-v1`，24 条稳定摘要，重复生成 Hash 一致。
- Demo 岗位投影：前端测试验证稳定 ID、无原始 URL、演示来源标识。
- Demo Mode 机会页：API 不可用时加载脱敏岗位、可搜索、可打开岗位详情；详情明确不展示完整 JD。
- Demo Career Loop 使用 `ACH_ENV=demo` 和专用 `ACH_DATA_DIR`；Demo runtime 缺少显式 `ACH_DATA_DIR` 会拒绝启动，演示路由在其他环境返回 403，核心继续使用现有 Career Core SQLite。
- Demo API 可在 `ACH_ENV=demo` 下不使用 launch token，仅绑定 `127.0.0.1`；数据目录由 `ACH_DATA_DIR` 指向独立目录，与真实用户库分离。
- 前端回归：23 个测试文件、67 个测试通过；生产构建通过。
- Demo Story 读模型：`GET /api/v1/career-loop/demo-story` 从现有 SQLite 只读组合岗位、申请、面试、知识提案和领域事件；历史页展示岗位到面试复盘步骤，知识页展示可反向追溯关联。
- JD 分析持久化：完整 Demo 闭环为演示岗位写入 3 条 `JobRequirement` proposal，保留原始 Evidence 引用和 `proposed` 审核状态；Demo Story 返回评分、能力 gap、Evidence ID 和要求列表，重复执行保持稳定 ID。
- Resume Review Gate v0.1：Demo 岗位写入 3 个 evidence-backed ResumePatch；每条可单独接受、拒绝、手动编辑并保存审核时间、用户来源、说明、Requirement ID 和 Evidence ID。
- 只有所有 Patch 均已审核、至少一条已接受后，用户才能创建不可变 ResumeRevision 快照；拒绝项排除，基础 ResumeBase 不变，申请仍为 `preparing` 并引用精确 Revision。
- Demo Story、历史和知识读模型读取岗位、JD Requirement、Evidence、Patch 审核事件、ResumeRevision 与 Application 稳定 ID；不存在的关联显示“尚未建立关联”。
- 真实本地 API 验收（2026-09-23）：使用临时独立 `ACH_DATA_DIR`、`ACH_ENV=demo` 启动 `127.0.0.1:8765`；POST `/api/v1/career-loop/demo-full` 返回 `application_fbdd11d28d86432cb74ee48a`、`interview_demo_fbdd11d28d86432cb74ee48a`，随后重新 GET Demo Story 仍返回 8 个步骤、4 类知识提案和完整关联，证明重读持久化成功。
- 本轮前端回归：24 个测试文件、68 个测试通过；`npm run build` 通过；后端 focused E2E 2 passed；Ruff `backend tests migrations scripts` 通过。
- 全量后端回归基线：本轮变更前 `718 passed, 5 skipped`；最终结果见本轮回归记录。
- 独立本地 HTTP + 进程重启验收（2026-09-23）：`ACH_DATA_DIR=%TEMP%/ach-resume-review-gate-20260923`；岗位 `opportunity_4a0d1f026edd89e3e11afe3694be250a`，申请 `application_fbdd11d28d86432cb74ee48a`，接受并手改 `patch_cbbabb4065401b997538e9ea`，接受 `patch_e75651e1963b3a36df4167c0`，拒绝 `patch_4493228e40647df83ac75e1a`，版本 `resume_revision_demo_target_83a14d40fb26dd09ecf0c151`。重启 API 后 GET Story 与 Application 仍读到相同 ID、Patch 决定及 `preparing` 状态。
- Story 实际返回 9 个步骤、3 个 JD Requirement proposal 链接、1 个 Evidence、3 个 Patch 和 1 个 ResumeRevision；Patch 对 proposal Requirement 的 ID 是 Demo Story 稳定投影，不伪造 Career Core 已接受的正式 Requirement 引用；API 未调用投递或外部平台。
- 最终全量后端回归（2026-09-23）：`719 passed, 5 skipped`；5 项均为 Windows symlink 创建权限限制。前端 `24 test files, 69 passed`，`npm --prefix apps/desktop run build` 通过，Ruff 与 `git diff --check` 通过。`npm run lint` 未配置；TypeScript 检查由 build 的 `tsc -b` 完成。
- 最终隔离闸门增补后 focused：`9 passed`（Demo runtime 要求独立目录、完整 Resume Review Gate、Application 与 migration downgrade）；前端仍为 69 passed，build/Ruff/diff check 通过。完整回归数字来自该闸门增补前的同一功能状态。
- 最终工作树复验（2026-09-23）：`.venv/Scripts/python.exe -m pytest -q` 为 `720 passed, 5 skipped`（5 项为 Windows symlink 创建权限限制）；`npm test -- --run` 为 24 个测试文件、71 项通过（含完整逐条审核/Revision 组件路径与保存失败提示）；`npm run build`、`.venv/Scripts/ruff.exe check backend tests migrations scripts` 与 `git diff --check` 均通过。裸系统 Python 缺少 Alembic/FastAPI 等依赖，collection 失败；不计为项目测试结果。仓库未配置 `npm run lint`。
- 本地服务实际检查：`http://127.0.0.1:5183` 返回 HTTP 200；`http://127.0.0.1:8783/health` 返回 HTTP 200、`environment=demo`。CUA 浏览器通道因 `unsupported Codex auth method: apikey` 未能执行可视操作或取得截图；未伪造截图。
- Legacy 原始 CSV 只读复核 SHA-256 仍为 `477ed75bb81dd2a66a1b06f91c8af5bfb5997704b6a0c4d0d7bf19b9482eef60cd`；本轮未向原始 `agent_rader` 写入。

## 尚未完成

- 浏览器可视操作/截图未完成：CUA 浏览器通道返回 `unsupported Codex auth method: apikey`。未伪造截图；组件测试、生产构建和真实 API 重启读取作为已取得证据。本地 Vite/API 健康检查分别返回 HTTP 200 / `environment=demo`。
- 浏览器截图和 Windows Tauri 包、端口冲突与退出清理验收仍未完成；自动化 API 和全量测试不能替代桌面/视觉验收。

## 下一步

最高优先级：修复 CUA 浏览器认证并完成可视端到端验收，随后执行 Tauri Windows 干净目录与 sidecar 生命周期、端口冲突及退出清理验收。
