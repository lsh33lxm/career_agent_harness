# v2.0 Autonomous Changelog

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
