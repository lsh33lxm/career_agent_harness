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
