# v0.1.0 端到端验收记录

## 已验证

- Legacy 核心岗位 CSV 只读审计：492 行，源文件 SHA-256 `477ed75bb81dd2a66a1b06f91c8af5bfb5997704b6a1c0d7bf19b9482eef60cd`。
- 脱敏演示生成：固定 seed `ach-demo-v1`，24 条稳定摘要，重复生成 Hash 一致。
- Demo 岗位投影：前端测试验证稳定 ID、无原始 URL、演示来源标识。
- Demo Mode 机会页：API 不可用时加载脱敏岗位、可搜索、可打开岗位详情；详情明确不展示完整 JD。
- 前端回归：23 个测试文件、67 个测试通过；生产构建通过。

## 尚未完成

- Demo 数据尚未写入 Career Core，因此演示模式的申请、简历审核和面试复盘不能伪装成持久化成功；真实持久化链路仍需本地 API 和数据库。
- Tauri sidecar、Windows 安装包、端口冲突和退出清理尚未在本阶段重新验收。
- 后端 pytest/ruff 当前环境不可执行，integration 工作树没有 `.venv`，系统 Python 未安装工具。

## 下一步

把 Demo 数据导入隔离的演示数据库，并为岗位 → 证据 → 目标简历 → 申请 → 面试 → 历史增加离线 E2E；随后执行 Tauri Windows 干净目录验收。
