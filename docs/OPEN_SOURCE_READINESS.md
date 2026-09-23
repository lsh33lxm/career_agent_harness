# v0.1.0 Demo Ready 发布检查

## Desktop Verification Gate v0.1（2026-09-23）

- Windows Tauri x64 release + NSIS bundle 在独立 ignored Cargo target 中构建通过；安装至独立临时目录后，使用显式 Demo 环境与专属 `ACH_DATA_DIR` 完成首次启动、SQLite migrations 与本地 API health/read 请求。sidecar stdout/stderr 写入专属 `logs/desktop-sidecar.log`。
- 真实 sidecar 端口冲突注入（loopback listener 持有 46282）验证自动重试至 51643；窗口关闭后应用及 sidecar 均退出。发布 EXE PE subsystem=2（GUI）。旧 sidecar 失败路径日志含 Python traceback、退出码、readiness 超时；UI 启动状态有中文错误提示。
- Demo sidecar 使用当前 Python 源码重建用于 NSIS 构建；原始 ignored sidecar 输入文件以 SHA-256 `692fd89ab87bd7c1936f3af50febee39d0a9a6c6002ab2c9f16fd05e479fe8091` 校验并恢复，避免改写既有产物。
- Playwright 完整 UI 工作流未得到结果：Windows runner 卡在 teardown，锁定浏览器下载因 Google Storage 网络超时。本轮没有可视截图，不得据桌面窗口启动与 API 请求推断 Resume Review 的完整 UI 链路已经通过。
- 桌面 Gate 当前 **NO-GO**；发布构建、Demo sidecar 启动、日志、端口恢复、关闭清理已通过，浏览器逐 Patch/Revision/Application/历史/知识交互与截图仍是发布前阻塞。
- 本轮运行与精确报错、端口、数据目录和证据路径详见 [`E2E_ACCEPTANCE.md`](E2E_ACCEPTANCE.md) 的 Desktop Verification Gate 记录。安装包与测试数据均在 Git 忽略目录；未推送、未写外部平台、未触碰原始 `agent_rader`。

## 已完成

- integration 工作树保持原有 Career Core、证据约束、人工审核和 Tauri + Python sidecar 边界。
- 新增只读岗位库审计脚本 `scripts/audit_job_db.py`，拒绝 `<JOB_DB_PATH>` 占位路径，不导出原文。
- 新增 `docs/data-audit.md`、`docs/demo-data-policy.md`、`docs/demo-story.md`，明确真实数据和再分发边界。
- `.gitignore` 覆盖 SQLite 临时文件、岗位库、导出、日志、缓存、备份和个人材料。
- 前端支持显式 `VITE_DEMO_MODE=true` 或 `window.__ACH_CONFIG__.demoMode=true` 的中文演示标识；无 token 时不再显示英文内部错误。
- Legacy 核心岗位 CSV 已完成只读审计：492 行，使用固定 seed 生成 24 条脱敏岗位摘要；Demo Mode 机会页支持离线搜索和详情查看。
- 新增隔离 Demo Career Loop：`ACH_ENV=demo` + 独立 `ACH_DATA_DIR` 时，完整岗位到申请、面试准备和复盘提案由本地 API 持久化；真实模式仍要求 launch token。
- 新增只读 Demo Story 聚合：历史页与知识页从现有 Core SQLite 反向展示岗位、简历、申请、面试、知识提案和事件链；不创建第二套数据库，也不将 Demo 提案提升为 Career Core 事实。
- Demo JD 分析现在通过现有 `JobService.propose_requirement` 写入 `JobRequirement` proposal；3 条要求各自带稳定 ID、Evidence 引用和人工审核状态，重复闭环不会重复创建。
- Demo 简历修改维持逐 Patch review gate：接受、拒绝、用户手动编辑均产生 Career Core 审核修订及领域事件；Evidence 与 JD Requirement 使用稳定引用，岗位证据不被标记为个人事实。
- 用户单独触发生成不可变 ResumeRevision 快照；仅包含接受 Patch，基础简历不覆盖；Application 在 `preparing` 状态精确引用目标版本，不会自动标记已投递。
- Demo Story / 历史 / 知识显示岗位、JD Requirement、Evidence、Patch 决定、ResumeRevision、Application 的稳定 ID；演示写入 API 在非 Demo Mode 被禁用。
- Demo runtime 要求显式 `ACH_DATA_DIR`，缺少时拒绝启动，防止默认落入用户正式数据目录。Demo Story 中 proposal Requirement ID 是稳定投影，Career Core 的正式 Patch Requirement 引用仍要求 Requirement 已接受。

## 验证证据

```text
npm --prefix apps/desktop test -- --run  -> 23 files, 67 tests passed
npm --prefix apps/desktop run build     -> Vite production build passed
python scripts/build_demo_dataset.py ... -> 492 source rows, 24 selected, fixed-seed output
\.venv\Scripts\python.exe -m pytest -q tests/integration/test_full_demo_career_loop.py -> 1 passed
\.venv\Scripts\ruff.exe check backend tests migrations scripts -> All checks passed
git diff --check                         -> passed
```

此前记录的验证（历史结果）：

```text
npm --prefix apps/desktop test -- --run  -> 24 files, 68 tests passed
npm --prefix apps/desktop run build     -> Vite production build passed
.venv/Scripts/python.exe -m pytest -q tests/integration/test_full_demo_career_loop.py -> 2 passed
.venv/Scripts/ruff.exe check backend tests migrations scripts -> All checks passed
.venv/Scripts/python.exe -m pytest -q -> 719 passed, 5 skipped（Windows symlink 创建权限限制）
```

使用临时目录 `ACH_DATA_DIR=%TEMP%/ach-demo-e2e-integration` 启动 Demo API 后，实际 POST 完整闭环并重新 GET `/api/v1/career-loop/demo-story`；返回 8 个链路步骤和岗位、申请、面试、知识关联。CUA 浏览器截图未完成，原因是当前 Codex 浏览器通道拒绝 `apikey` 认证配置。

Resume Review Gate 本地 HTTP 重启验收数据位于临时隔离目录 `%TEMP%/ach-resume-review-gate-20260923`，完成逐 Patch 接受/拒绝/手动编辑、Revision 快照、申请引用与进程重启读取。完整后端回归 `719 passed, 5 skipped`；新增 Demo 数据目录闸门后 focused `9 passed`；前端 `24 test files, 69 passed`，生产构建、Ruff 与 diff check 通过。CUA 截图因认证方式 `apikey` 不受支持而阻塞；本地 Vite/API 可运行，但未通过浏览器可视操作。

最终工作树复验（2026-09-23）：`.venv/Scripts/python.exe -m pytest -q` 为 `720 passed, 5 skipped`（5 项因 Windows symlink 创建权限限制跳过）；`npm test -- --run` 为 24 个测试文件、71 项通过（含完整逐条审核/Revision 组件路径与保存失败提示）；`npm run build`（含 `tsc -b`）、`.venv/Scripts/ruff.exe check backend tests migrations scripts` 和 `git diff --check` 通过。仓库未配置 `npm run lint`；裸系统 Python 因缺少项目依赖造成的 collection error 未计入有效结果。

本轮记录 ID：岗位 `opportunity_4a0d1f026edd89e3e11afe3694be250a`；接受并手动编辑 Patch `patch_cbbabb4065401b997538e9ea`；接受 Patch `patch_e75651e1963b3a36df4167c0`；拒绝 Patch `patch_4493228e40647df83ac75e1a`；ResumeRevision `resume_revision_demo_target_83a14d40fb26dd09ecf0c151`；Application `application_fbdd11d28d86432cb74ee48a`。持久化文件 `%TEMP%/ach-resume-review-gate-20260923/career_harness.db` 使用 `ACH_ENV=demo` 与显式 `ACH_DATA_DIR` 隔离；API 进程重启后仍读到相同审核结果、版本和申请引用。

Vite `http://127.0.0.1:5183` 和 API `http://127.0.0.1:8783/health` 均实际返回 HTTP 200，API 报告 `environment=demo`。CUA 浏览器因 `unsupported Codex auth method: apikey` 未能完成截图/点击验收；未伪造视觉证据。原始 CSV SHA-256 复核为 `477ed75bb81dd2a66a1b06f91c8af5bfb5997704b6a0c4d0d7bf19b9482eef60cd`，原始 `agent_rader` 未被写入。

## 发布阻塞

1. Legacy 可访问，但完整岗位库的再分发权仍未确认；当前只发布有限摘要，不发布完整 JD 或 URL。
2. 当前环境未提供 PolyForm Noncommercial 1.0.0 与 CC BY-NC-SA 4.0 的正式法律文本，不能自行改写许可证全文；正式发布前必须补齐经核验的许可证文件。
3. Tauri sidecar 的正式 Windows 安装包和干净环境验收尚未在本切片中重新执行。

## 下一步

下一步优先修复 CUA 浏览器认证并完成截图验收，然后执行 Tauri Windows 干净目录、sidecar 生命周期、端口冲突和退出清理验收。
