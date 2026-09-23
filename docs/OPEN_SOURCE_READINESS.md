# v0.1.0 Demo Ready 发布检查

## 已完成

- integration 工作树保持原有 Career Core、证据约束、人工审核和 Tauri + Python sidecar 边界。
- 新增只读岗位库审计脚本 `scripts/audit_job_db.py`，拒绝 `<JOB_DB_PATH>` 占位路径，不导出原文。
- 新增 `docs/data-audit.md`、`docs/demo-data-policy.md`、`docs/demo-story.md`，明确真实数据和再分发边界。
- `.gitignore` 覆盖 SQLite 临时文件、岗位库、导出、日志、缓存、备份和个人材料。
- 前端支持显式 `VITE_DEMO_MODE=true` 或 `window.__ACH_CONFIG__.demoMode=true` 的中文演示标识；无 token 时不再显示英文内部错误。

## 验证证据

```text
npm --prefix apps/desktop test -- --run  -> 23 files, 67 tests passed
npm --prefix apps/desktop run build     -> Vite production build passed
python scripts/audit_job_db.py '<JOB_DB_PATH>' -> rejected (expected; real path missing)
git diff --check                         -> passed
```

## 发布阻塞

1. 用户消息提供的是字面 `<JOB_DB_PATH>`，没有可验证的原始岗位数据库，因此无法生成真实脱敏演示数据、6000+ 统计或字段级公开结论。
2. 当前环境未提供 PolyForm Noncommercial 1.0.0 与 CC BY-NC-SA 4.0 的正式法律文本，不能自行改写许可证全文；正式发布前必须补齐经核验的许可证文件。
3. Tauri sidecar 的正式 Windows 安装包和干净环境验收尚未在本切片中重新执行。

## 下一步

收到真实数据库路径并完成来源许可审阅后，运行审计脚本，再实现可重复脱敏生成器和 Demo Mode seed；之后执行 Tauri 安装、启动、离线查看和截图验收。
