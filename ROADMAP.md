# Roadmap

本路线图以 integration 真实代码、迁移、测试和审计结果为准。Legacy 始终只读；canonical cutover 与 Feishu 外部写入需要额外授权。

| 优先级 | Slice | 状态 | 退出条件 |
| --- | --- | --- | --- |
| P0 | Core invariants、typed repositories/API、Today、Capability、Opportunity、Evidence provenance | DONE | backend regression 通过 |
| P0 | 观复视觉 baseline、Logo derivative、responsive validation | DONE | frontend tests/build + browser evidence |
| P0 | Legacy inventory、archive、reconciliation、dry-run、backup/restore | DONE（reversible subset） | exact hashes/provenance/reimport/restore |
| P0 | Feishu deterministic offline projection | DONE（offline） | schema/mapping/focused tests |
| P1 | Projects/Resume/Context 只读客户端 | 部分完成 | Projects/Resume narrow clients 已合入；补 fixture/Context client |
| P1 | Legacy structured mapping staging | PLANNED；canonical部分需用户authority | duplicate/conflict/versioned mapping report |
| P1 | Real-data read-model fixtures and UI acceptance | Evidence rehearsal DONE；career数据待批准 | no mock fallback, exact provenance |
| P1 | L2 runner/result contract | PLANNED | separate contract, review and bounded implementation |
| P2 | Feishu external sync | BLOCKED_EXTERNAL_ACTION | credentials、permission、sync contract |
| P2 | Legacy canonical cutover | NEEDS USER AUTHORITY | identity/grade/mapping/candidate decision and rollback approval |
| P2 | Live CLI/ATS/browser actions | PLANNED / gated | explicit executor contract and production approval |
| P3 | Generic multi-agent runtime/plugin marketplace | OUT OF SCOPE | only after proven product need |

## Current verification

2026-09-21：backend `602 passed, 5 skipped`；frontend `56 passed`，build passed；focused migration/evidence/Feishu `27 passed`；Ruff and diff check passed。跳过项均为 Windows symlink 权限/能力限制。

## Data and authority gates

Inventory 2,426 files / 377,785,991 bytes，source metadata unchanged；archive preserves 2,205 paths，17 deferred。35 duplicate JD URLs、S/C grade differences、82 question mappings、270 unstarted coding plans remain staging/deferred. 生产数据库未导入，Legacy 目录未修改。
