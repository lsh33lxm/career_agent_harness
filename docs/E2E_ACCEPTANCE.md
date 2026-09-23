# v0.1.0 端到端验收记录

## 已验证

- Legacy 核心岗位 CSV 只读审计：492 行，源文件 SHA-256 `477ed75bb81dd2a66a1b06f91c8af5bfb5997704b6a1c0d7bf19b9482eef60cd`。
- 脱敏演示生成：固定 seed `ach-demo-v1`，24 条稳定摘要，重复生成 Hash 一致。
- Demo 岗位投影：前端测试验证稳定 ID、无原始 URL、演示来源标识。
- Demo Mode 机会页：API 不可用时加载脱敏岗位、可搜索、可打开岗位详情；详情明确不展示完整 JD。
- 完整 Demo Career Loop：通过 `/api/v1/career-loop/demo-full` 在隔离 SQLite 中真实持久化岗位 admission、Evidence、Target Profile、Resume Patch/Render、申请状态推进、Interview schedule/complete、面试准备提案和复盘提案；重复调用不会创建第二份核心实体。
- Demo API 可在 `ACH_ENV=demo` 下不使用 launch token，仅绑定 `127.0.0.1`；数据目录由 `ACH_DATA_DIR` 指向独立目录，与真实用户库分离。
- 前端回归：23 个测试文件、67 个测试通过；生产构建通过。
- Demo Story 读模型：`GET /api/v1/career-loop/demo-story` 从现有 SQLite 只读组合岗位、申请、面试、知识提案和领域事件；历史页展示岗位到面试复盘步骤，知识页展示可反向追溯关联。
- JD 分析持久化：完整 Demo 闭环为演示岗位写入 3 条 `JobRequirement` proposal，保留原始 Evidence 引用和 `proposed` 审核状态；Demo Story 返回评分、能力 gap、Evidence ID 和要求列表，重复执行保持稳定 ID。
- 真实本地 API 验收（2026-09-23）：使用临时独立 `ACH_DATA_DIR`、`ACH_ENV=demo` 启动 `127.0.0.1:8765`；POST `/api/v1/career-loop/demo-full` 返回 `application_fbdd11d28d86432cb74ee48a`、`interview_demo_fbdd11d28d86432cb74ee48a`，随后重新 GET Demo Story 仍返回 8 个步骤、4 类知识提案和完整关联，证明重读持久化成功。
- 本轮前端回归：24 个测试文件、68 个测试通过；`npm run build` 通过；后端 focused E2E 2 passed；Ruff `backend tests migrations scripts` 通过。
- 完整后端回归：`717 passed, 5 skipped`；跳过项均为 Windows symlink 权限限制，没有失败。

## 尚未完成

- 浏览器端完整链路需要以 `ACH_ENV=demo` 启动本地 API 后点击“运行完整演示闭环”；纯静态 Vite 页面在 API 不可用时只提供脱敏岗位浏览，不会伪造保存成功。当前环境的 CUA 浏览器通道因 Codex `apikey` 认证配置不支持而无法完成截图验证。
- Tauri sidecar、Windows 安装包、端口冲突和退出清理尚未在本阶段重新验收。
- 后端 pytest/ruff 当前环境不可执行，integration 工作树没有 `.venv`，系统 Python 未安装工具。

## 下一步

为 Demo Loop 增加历史/知识页面的显式事件链读模型和操作入口；随后执行 Tauri Windows 干净目录验收。
