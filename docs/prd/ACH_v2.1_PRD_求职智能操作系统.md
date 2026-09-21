# Agent Career Harness v2.1：求职智能操作系统

版本：v2.1

日期：2026-09-22
实现基线：`292ad82`（integration worktree）

## 1. 本次目标与结论

Agent Career Harness 已从页面原型形成可安装的本地中文职业工作台：Career Core 管理权威状态，Artifact/Evidence 保存来源，Legacy 数据以只读投影进入机会与知识页面，插件、模型、GitHub 项目分析、简历、岗位、能力和 Wiki 通过同一审计边界协作。本轮恢复正确的“观复”桌面图标，并补齐 Wiki graph 与 health governance。

状态定义：**已完成**表示代码、测试和本地构建均存在；**部分完成**表示安全的本地闭环存在但高级能力或外部连接未完成；**阻塞**表示需要凭据、条款许可或用户权威。

## 2. 已实现模块与路径

| 模块 | 状态 | 主要路径 |
|---|---|---|
| Career Core、Evidence、Approval、Audit | 已完成 | `backend/career_harness/core/`、`backend/career_harness/db/` |
| Legacy 岗位/面试/问题只读导入 | 已完成（非 canonical） | `backend/career_harness/services/legacy_import_service.py` |
| Opportunity Radar、去重、排名、admission | 已完成（本地/离线来源） | `backend/career_harness/services/opportunity_radar_service.py` |
| Knowledge 导入、chunk、hybrid retrieval、引用 | 已完成 | `backend/career_harness/db/knowledge_repository.py` |
| Wiki proposal、revision、diff、rollback、graph、health | 已完成 | `backend/career_harness/api/knowledge.py` |
| Resume proposal、revision、HTML/PDF、ATS 检查 | 已完成（本地 renderer） | `backend/career_harness/services/resume_studio_service.py` |
| 模型配置与安全密钥 | 已完成；真实连接待凭据 | `backend/career_harness/services/model_provider_service.py` |
| GitHub 只读项目分析 | 已完成；公网验收受网络影响 | `backend/career_harness/services/github_project_service.py` |
| Windows 桌面/sidecar/NSIS | 已完成 | `apps/desktop/src-tauri/` |
| “观复”主题与正确图标 | 已完成 | `apps/desktop/src/styles.css`、`apps/desktop/src-tauri/icons/` |

## 3. Career Core 与真值边界

- Career Core/SQLite：用户确认的职业事实、经历、简历、Opportunity、Application 与 Outcome 的规范来源。
- Artifact Store/Evidence：不可变原文、hash、快照和精确 provenance。
- Knowledge staging：外部文档、Legacy 数据、岗位、网页和项目扫描结果；不会自动成为 Fact。
- Wiki：带 revision、引用和治理检查的派生知识；LLM/插件只能创建 draft/proposal。
- Web、桌面、Feishu：投影，不拥有业务真值。
- 模型与执行器：产生推断或执行结果，不拥有批准权。

## 4. Knowledge / RAG / Wiki / Memory

当前 Knowledge 支持 Markdown、HTML、PDF、DOCX 和文本导入，原始 bytes 进入 Artifact Store；内容被确定性分块并建立 lexical + 本地字符向量 hybrid index。检索返回分数、片段、EvidenceRef、source locator、authority 与 revision；疑似 prompt injection 默认隔离。

Wiki 支持 proposal 审核、revision history、line diff、rollback、显式页面 link、当前 graph 和 health score。Health 检查孤立页面、重复标题、过期 revision link、缺少引用和提示注入；检查只读，不自动发布、删除或批量修复。

长期记忆仍为**未完成**：profile/preference/fact/task/interest memory、作用域、确认、tombstone、consolidation 和 affinity 尚无独立持久化契约。实现时必须复用 proposal/approval/audit，不得让记忆授予工具权限或覆盖本轮用户要求。

## 5. 职位、简历、面试与申请流程

已可运行的主链：Legacy/手动来源 → 原文与 provenance → staging → fingerprint/去重 → match/gap/rank → 用户 admission → Opportunity。Resume Studio 支持 TargetProfile、EvidenceRef 约束 patch、用户审核、不可变 revision、主题预览、PDF 与 ATS 检查。Application 与 Outcome 已有独立状态模型和只读投影。

公司研究、STAR 面试准备、follow-up 和结果归档已有部分领域基础，尚未形成一个单按钮离线编排任务。真实 ATS 提交、批量沟通、验证码处理和外部写入不在自动执行范围。

## 6. 当前主题保护

所有新增 UI 继续复用深墨绿、暖纸色、暖白、少量金色、现有字体/间距/圆角/阴影与 AppShell。未复制任何上游项目的前端。桌面、EXE、安装包和平台图标已从 `apps/desktop/public/brand-icon-clean.png` 重新生成，早期黄色 “AI” 占位图标已移除。

## 7. 上游能力映射与许可证复核

下表 SHA 由 2026-09-22 的 `git ls-remote`/浅克隆只读复核获得。当前实现没有复制任何上游源码；均为基于公开行为和本项目契约的等价实现或后续参考。

| 上游 | 审阅 SHA | 许可证 | 采用方式与落点 |
|---|---|---|---|
| Pickle-Pixel/ApplyPilot | `4a8d521f67f5139811c0a910ef37410f8e6d836a` | AGPL-3.0 | 仅行为参考：阶段流水线、dry-run、事实保护 |
| DanielPan12/JobHuntBot | `0ccaa11ebd07627e79a87d991504878d2ab9a9ed` | MIT | 行为参考：onboarding、resume routing、never-guess、阻塞状态 |
| shengjidaguai-china/BossHunter | `5ce43e3968d6d3655be45882df9fbb9b87d84b94` | PolyForm Noncommercial 1.0.0 | 仅行为参考：中文平台 adapter、限流、预览确认 |
| MadsLorentzen/ai-job-search | `120f476a089358363ceaf2528f52edf2854994bd` | MIT | 行为参考：setup→outcome、portal skill、drafter/reviewer |
| career-ops-hq/career-ops | `dda9b8c543ad99086d03809a3fca9fbfbbafa426` | MIT | 行为参考：local-first、fingerprint、评估与 follow-up |
| jimmyzheng1027/CapyMock | `b3376f6f713bab3017c0b6ae9814e7fca18f1b72` | 未发现 LICENSE | 隔离的行为参考：Agent loop、事件、模型抽象；不复制 |
| xiao-chen-ai/seeking-stars | `a2982fcb04b456ed7bb88428d042bd3367f32531` | 自定义非商业许可 | 仅 README 行为参考；公开树仅 README/LICENSE |
| xinhuangcs/CareerDesk | `4306cfcce1609b0234ab3a6859cc299ca1206a45` | MIT | 行为参考：本地看板、trusted operation、revision/undo |
| JOYCEQL/magic-resume | `005289cf5f30b513f9e9605955255d75173c60a2` | Apache-2.0 + 严格商业限制 | 仅功能/数据结构参考；不复制代码、模板或主题 |
| Tencent/WeKnora | `33c0333ec9474a6d090bab346e1d631a842bafaf` | MIT + `THIRD_PARTY_NOTICES.md`/`licenses/` | 等价实现本地知识治理；远程 adapter 保持隔离 |

## 8. 插件、工具与执行安全

Plugin Manifest、Registry、Permission Gate、worker/plugin envelope、安装预览、quarantine、shadow run、switch 与 rollback 已存在。插件没有裸 SQLite、任意 shell 或隐式外部写权限。MCP scope、SourceConnector 全量/增量同步、通用任务 worker pool 和受控 Codex/Claude/OpenCode Runner 仍为**部分或未完成**。

外部文本全部按不可信输入处理；URL fetch 必须限制 host/协议/大小/超时并防 SSRF；密钥只进入 Windows Credential Manager；普通日志不得记录密钥、简历正文或 launch token。提示词不能扩大后端权限。

## 9. 实现状态矩阵

| 能力 | 状态 | 下一动作 |
|---|---|---|
| Career Core / Evidence / Audit | 已完成 | 保持兼容并扩展精确引用 |
| Knowledge import/chunk/hybrid search/citation | 已完成 | 增加真实 embedding/rerank 可选 adapter |
| Wiki revision/diff/rollback/graph/health | 已完成 | 增加页面编辑、移动和 lint 修复 proposal |
| Memory governance | 未完成 | 先实现 scoped proposal/confirm/tombstone |
| SourceConnector/sync cursor/delete safety | 部分完成 | 统一现有 GitHub、Legacy、Feishu adapter 契约 |
| Task retry/cancel/dead-letter/worker pool | 部分完成 | 建立 version/attempt 防旧任务覆盖 |
| Opportunity/Resume/Application | 已完成本地核心 | 编排离线端到端任务和公司/面试产物 |
| 外部 ATS/邮件/Feishu/Notion 写入 | 阻塞 | 需要凭据、条款与逐次用户批准 |
| MCP/CLI Runner | 部分完成 | 只读默认、写权限审批、sandbox 与审计 |
| 语音面试 | 计划 | 先保持文本面试，feature flag 后置 |

## 10. 测试与构建结果

- Backend：`658 passed, 5 skipped`；5 项均为 Windows symlink 创建权限限制。
- Frontend：`20 test files, 55 passed`。
- Ruff：`backend tests migrations` 通过。
- TypeScript/Vite：production build 通过。
- Wiki focused：backend `9 passed`，Knowledge 页面测试通过。
- Desktop：PyInstaller sidecar 与 Tauri NSIS release 构建通过。
- 安装包：`apps/desktop/src-tauri/target/release/bundle/nsis/Agent Career Harness_0.1.0_x64-setup.exe`。

## 11. 未完成与阻塞

- Memory、统一 SourceConnector、通用 Task queue、MCP scope 和 CLI sandbox 尚未达到本 PRD 的完整目标。
- GraphRAG、真实 dense embedding/rerank、OCR/VLM/ASR、表格/图片/Office 全格式解析仍需可替换 adapter。
- 真实模型对话需要用户配置凭据并明确允许发送的数据；连接测试成功前只能显示“尚未配置/未验证”。
- 外部 ATS、Gmail、Notion、Feishu 等真实写入需要凭据、目标权限、条款复核和逐次批准。
- Legacy → canonical authority cutover 仍需用户权威；当前 7,575 条导入记录保持历史投影。
- CapyMock 无明确许可证；AGPL、PolyForm、自定义非商业和 Magic Resume 限制代码均不得复制进发行物。

## 12. 下一阶段具体顺序

1. 实现 scoped Memory proposal → user confirm/reject/edit/delete/tombstone → search/revision。
2. 抽取统一 SourceConnector，迁移本地文件夹、GitHub 与现有 Legacy importer，加入 cursor、delete safety、sync log。
3. 建立 versioned Task queue：retry/backoff/cancel/resume/dead-letter/attempt guard/observability。
4. 将 Opportunity → Resume proposal → ATS → company research → STAR → Application audit 串成离线 E2E。
5. 补充 MCP scope 与受控 CLI Runner；默认只读，写入必须 approval，网络/文件系统由后端强制。
6. 在以上契约稳定后接入可选 embedding、rerank、OCR/VLM 和 WeKnora adapter。

需要用户之后确认的事项仅包括：Legacy canonical authority、真实模型数据发送、外部连接凭据/条款、任何真实投递或消息写入，以及受限制许可证的商业授权。
