# v0.1.0 Demo Ready 发布检查

## 已完成

- integration 工作树保持原有 Career Core、证据约束、人工审核和 Tauri + Python sidecar 边界。
- 新增只读岗位库审计脚本 `scripts/audit_job_db.py`，拒绝 `<JOB_DB_PATH>` 占位路径，不导出原文。
- 新增 `docs/data-audit.md`、`docs/demo-data-policy.md`、`docs/demo-story.md`，明确真实数据和再分发边界。
- `.gitignore` 覆盖 SQLite 临时文件、岗位库、导出、日志、缓存、备份和个人材料。
- 前端支持显式 `VITE_DEMO_MODE=true` 或 `window.__ACH_CONFIG__.demoMode=true` 的中文演示标识；无 token 时不再显示英文内部错误。
- Legacy 核心岗位 CSV 已完成只读审计：492 行，使用固定 seed 生成 24 条脱敏岗位摘要；Demo Mode 机会页支持离线搜索和详情查看。

## 验证证据

```text
npm --prefix apps/desktop test -- --run  -> 23 files, 67 tests passed
npm --prefix apps/desktop run build     -> Vite production build passed
python scripts/build_demo_dataset.py ... -> 492 source rows, 24 selected, fixed-seed output
git diff --check                         -> passed
```

## 发布阻塞

1. Legacy 可访问，但完整岗位库的再分发权仍未确认；当前只发布有限摘要，不发布完整 JD 或 URL。
2. 当前环境未提供 PolyForm Noncommercial 1.0.0 与 CC BY-NC-SA 4.0 的正式法律文本，不能自行改写许可证全文；正式发布前必须补齐经核验的许可证文件。
3. Tauri sidecar 的正式 Windows 安装包和干净环境验收尚未在本切片中重新执行。

## 下一步

下一步是把脱敏摘要导入隔离 Demo 数据库，打通申请/简历/面试持久化 E2E，再执行 Tauri 安装、启动、离线查看和截图验收。
