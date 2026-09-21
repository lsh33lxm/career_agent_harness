# v2.0 Autonomous Changelog

## 2026-09-22

- 完成 Windows Tauri 2 桌面产品化：PyInstaller one-file sidecar、bundle migration resources、随机 loopback 端口、临时 token 注入、Data Root 日志与完整进程树回收。
- 生成 NSIS 安装包并完成隔离干净安装；首次启动自动建库，重启后数据持久，窗口关闭后 sidecar 与监听端口均释放。
- 在干净安装数据库执行真实 Legacy 只读导入：首轮读取/新增 7,575、重复 684、失败 0；第二轮新增 0、未变化 7,575；导入前后源签名一致，Python 岗位查询与 provenance 抽样通过。
- 新增只读 Legacy 知识概览 API 与知识页真实内容：展示岗位/面试/问题/刷题计数、技能/公司/地点趋势、近期问题和面试 provenance；历史内容保持未确认投影。
- Today 在 Core 队列为空时读取真实历史岗位数量并提供“机会”入口，不自动创建 Opportunity 或修改用户优先级。局部验证 backend `2 passed`、frontend `7 passed`，frontend full `55 passed`，Vite build/Ruff/diff check 通过。

## 2026-09-21

- 开始 Slice A Plugin Foundation。
- 确认 integration 基线 `084017c` 干净，v1.5 backend/frontend 回归已完成。
- 建立自主执行状态、决策和 blocker ledger。
- 完成 Slice A Plugin Foundation：manifest/schema、scoped runner、0014 migration、echo worker、local KB read-only adapter、API 和 /plugins UI。
- 完成 focused acceptance、migration downgrade、backup/restore rehearsal；全量 backend 613 passed, 5 skipped，frontend 56 passed，build/Ruff/diff check 通过。
- 下一入口切换为 Slice B Career Knowledge / Wiki；真实外部写入仍保持 blocked。
- 完成 Slice B Career Knowledge / Wiki：`0015_knowledge_foundation`、Artifact/Evidence provenance、Markdown/HTML/DOCX/PDF 文本导入、确定性 local search、proposal review、diff/rollback/index rebuild、WeKnora read-only blocked adapter、知识 API 与 `/knowledge` 页面。
- Slice B 验证：focused knowledge `6 passed`；migration/backup `50 passed`；backend `619 passed, 5 skipped`；frontend `56 passed`；Vite build、Ruff、diff check 通过。
- 下一入口切换为 Slice C Resume Studio；Resume 外部模板与真实 ATS/投递写入仍保持 proposal-only/blocked。
- 完成 Slice C Resume Studio：`0016_resume_studio`、TargetProfile、target/patch refs、自有 HTML/CSS 模板、确定性 PDF、Artifact、ATS report、diff/provenance、authenticated API 与前端 Studio panel。
- 2026-09-21：完成 Slice C completion audit：Typst renderer 改为 sandbox/plugin contract，补齐 compiler provenance、unknown migration semantics、immutable render review、EvidenceRef-backed local draft promotion；focused 8 passed，backend full 634 passed/5 skipped，frontend 58 passed，build/Ruff/diff check passed。
- 2026-09-21：完成 Slice D completion audit：加入 `0019_opportunity_radar_ranking_policy`、可解释多维 ranking、evidence coverage 明示、source retry/rate/disable policy、policy API 与 frontend score projection；focused 8 passed，migration/backend subset 56 passed，frontend 58 passed，build/Ruff/diff check passed。
- Slice C focused backend/API/migration/restore `59 passed`；backend full `622 passed, 5 skipped`；frontend `57 passed`；Vite build、Ruff、diff check 通过。
- 下一入口切换为 Slice D Opportunity Radar；真实抓取器和自动投递保持 blocked。
- 完成 Slice D Opportunity Radar：`0017_opportunity_radar`、JobSource contract、manual/offline sources、Artifact/Evidence provenance、字段规范化、URL/content dedupe、match/gap/deal-breaker ranking、user-only admission、Resume proposal seed、API 与 Opportunities staging UI。
- Slice D focused backend/API/migration `5 passed`；backend full `627 passed, 5 skipped`；frontend `58 passed`；Vite build、backup/restore、Ruff、diff check 通过。
- 下一入口切换为 Slice E Lifecycle / Replacement；真实 crawler、portal 和 ATS 写入保持 blocked。
- 完成 Slice E Plugin Lifecycle / Replacement：versioned registry、candidate staging、compatibility/license/permission diff、deterministic shadow run、preview-gated switch、manual rollback、update policy、audit summary、uninstall data-impact preview 与插件页生命周期控制。
- Slice E focused backend/API `9 passed`；backend full `629 passed, 5 skipped`；backup/restore/lifecycle rehearsal `9 passed`；frontend `58 passed`；Vite build、Ruff、diff check 通过。
- A-E local/offline slices 全部完成；真实 marketplace、第三方 crawler 与 external-write adapters 保持 blocked，等待独立授权。
- Completion audit correction：上述“全部完成”结论撤回。逐条审计发现 B-E 仍有权威执行提示词明确要求但未被实现或验证的项目；从 Slice B deterministic hybrid search 继续补齐。
- Slice B completion audit 补齐 deterministic hybrid lexical/vector scoring、可解释 score 分量与 prompt-injection 默认 quarantine；focused knowledge/API/contract `11 passed`，backend full `630 passed, 5 skipped`，frontend `58 passed`，Ruff/build/diff check 通过。
- Slice C completion audit 补齐隔离 renderer contract、compiler provenance、local draft 的 EvidenceRef promotion gate 和 immutable render review；Typst 在无 sandbox/compiler 时明确 disabled，不伪造成功。
- Slice D hardening 补齐 deadline/location/salary/freshness 与 evidence-aware ranking provenance、per-source retry/rate/disable policy、失败采集 fail-loud，以及显式 user-only atomic admission。
- Slice E completion audit 补齐 run latency/output/provenance/error metrics、离线 license/dependency/security scan、shadow output/error/provenance/latency comparison、audit summary 和 non-automatic rollback recommendation；migration `0021_plugin_lifecycle_observability` upgrade/downgrade 与 lifecycle rehearsal 通过。
- 最终独立回归：backend `646 passed, 5 skipped`；frontend `17 test files, 58 passed`；Vite build、Ruff `backend tests migrations`、`git diff --check` 全部通过。A–E 当前状态为 DONE（local/offline），真实 marketplace、第三方 crawler 与 external-write adapters 继续按 blocker ledger 隔离。
- 自治记录完成收口：更新 `AUTONOMOUS_EXECUTION_STATE.md`、`DECISIONS.md`、`BLOCKERS.md`，Git HEAD 保持 `164c440`。
- Final requirement hardening：补充 Plugin Manifest v1 示例、第三方 source/ref/commit + license/NOTICE/manual-review scan 证据、默认 quarantine、knowledge category scope/敏感字段脱敏、WeKnora `list` blocked contract、Plugins UI manifest/审计/更新策略/卸载影响，以及 migration `0022_job_source_terms_provenance`。
- Hardening verification：focused backend `32 passed`、Plugins UI `1 passed`；full backend `650 passed, 5 skipped`、frontend `18 files / 59 passed`；Vite build、Ruff `backend tests migrations` 与 `git diff --check` 通过。
- Independent hardening review：先后修复 quarantine 经 disable/rollback 绕过、旧 scan report 绕过、JSON/Bearer 脱敏遗漏、历史 terms 时间伪造与无效 manifest 示例；最终 APPROVE，P0/P1/P2/P3 none。
- 新增真实模型服务配置：OpenAI、Anthropic、DeepSeek、OpenAI-compatible，additive `0024`、Windows Credential Manager 密钥边界、脱敏 API/UI 与用户确认后的只读连接测试。合成安全存储 rehearsal、50 backend subset、backend full 654 passed/5 skipped、52 frontend tests/build 通过；无凭据时保持未配置，未伪造外部连接成功。
- 新增 bounded GitHub 项目分析：additive `0025`、GitHub-only URL policy、hooks-disabled shallow clone、file/byte/timeout limits、静态项目 profile、private token safe store、Project UI/provenance。backend full 656 passed/5 skipped、52 backend subset、53 frontend tests/build 和 migration rehearsal 通过；真实 GitHub fetch 因环境 443 不可达保持 external blocker。
