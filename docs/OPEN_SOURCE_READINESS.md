# v0.1.0 Demo Ready 发布检查

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
- Demo 简历修改保持 review-gated：闭环只创建 Evidence-backed ResumePatch proposal；用户需在 Resume Studio 审核后创建 ResumeRevision，避免自动把模型/规则建议提升为职业事实。
- `test_full_demo_career_loop.py` 已覆盖 Demo Patch 的用户审核和独立 ResumeRevision 创建，确认未审核内容不会进入最终版本。

## 验证证据

```text
npm --prefix apps/desktop test -- --run  -> 23 files, 67 tests passed
npm --prefix apps/desktop run build     -> Vite production build passed
python scripts/build_demo_dataset.py ... -> 492 source rows, 24 selected, fixed-seed output
\.venv\Scripts\python.exe -m pytest -q tests/integration/test_full_demo_career_loop.py -> 1 passed
\.venv\Scripts\ruff.exe check backend tests migrations scripts -> All checks passed
git diff --check                         -> passed
```

本轮实际验证：

```text
npm --prefix apps/desktop test -- --run  -> 24 files, 68 tests passed
npm --prefix apps/desktop run build     -> Vite production build passed
.venv/Scripts/python.exe -m pytest -q tests/integration/test_full_demo_career_loop.py -> 2 passed
.venv/Scripts/ruff.exe check backend tests migrations scripts -> All checks passed
.venv/Scripts/python.exe -m pytest -q -> 717 passed, 5 skipped（Windows symlink 权限限制）
```

使用临时目录 `ACH_DATA_DIR=%TEMP%/ach-demo-e2e-integration` 启动 Demo API 后，实际 POST 完整闭环并重新 GET `/api/v1/career-loop/demo-story`；返回 8 个链路步骤和岗位、申请、面试、知识关联。CUA 浏览器截图未完成，原因是当前 Codex 浏览器通道拒绝 `apikey` 认证配置。

## 发布阻塞

1. Legacy 可访问，但完整岗位库的再分发权仍未确认；当前只发布有限摘要，不发布完整 JD 或 URL。
2. 当前环境未提供 PolyForm Noncommercial 1.0.0 与 CC BY-NC-SA 4.0 的正式法律文本，不能自行改写许可证全文；正式发布前必须补齐经核验的许可证文件。
3. Tauri sidecar 的正式 Windows 安装包和干净环境验收尚未在本切片中重新执行。

## 下一步

下一步是执行 Tauri 安装、启动、离线查看和截图验收，并补充 Windows 端 sidecar/端口冲突/退出清理证据。
