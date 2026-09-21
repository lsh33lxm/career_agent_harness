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
- Slice C focused backend/API/migration/restore `59 passed`；backend full `622 passed, 5 skipped`；frontend `57 passed`；Vite build、Ruff、diff check 通过。
- 下一入口切换为 Slice D Opportunity Radar；真实抓取器和自动投递保持 blocked。
- 完成 Slice D Opportunity Radar：`0017_opportunity_radar`、JobSource contract、manual/offline sources、Artifact/Evidence provenance、字段规范化、URL/content dedupe、match/gap/deal-breaker ranking、user-only admission、Resume proposal seed、API 与 Opportunities staging UI。
- Slice D focused backend/API/migration `5 passed`；backend full `627 passed, 5 skipped`；frontend `58 passed`；Vite build、backup/restore、Ruff、diff check 通过。
- 下一入口切换为 Slice E Lifecycle / Replacement；真实 crawler、portal 和 ATS 写入保持 blocked。
