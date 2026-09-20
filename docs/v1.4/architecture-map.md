# Agent Career Harness 当前架构

观察基点：integration `2e279ba`，2026-09-21。Shared contract：`0.17.0` / D-027。
历史基线与各阶段变更见 Git 历史和 `integration-log.md`；以下描述当前实现。

## Runtime

```text
React 19 / TypeScript / Vite → localhost FastAPI
                                   ├─ TodayService (pure policy + exact repositories)
                                   ├─ Opportunity commands/read + USER priority
                                   ├─ CapabilityWorkspace + Capability Inbox review
                                   ├─ Evidence metadata/provenance reads + Project metadata read
                                   └─ Resume/Application/Outcome read repositories
Career services → typed domain repositories → SQLite migrations 0001–0013
                → generic revisions / DomainEvent / idempotency / outbox
AppPaths → career_harness.db + content-addressed artifacts + backups + logs
Legacy read-only → inventory → archive index → disposable provenance DB → restore rehearsal
TodayQueue → Feishu offline JSON preview (no transport)
Project/Gap → L1 ManualExecutor → proposed task (no project file write)
Exact context → L2 preview (no subprocess/provider inference)
```

Tauri 2 shell 存在；本轮没有重建 sidecar 生命周期、原生打包或自动 token 注入。
Web 通过 typed API，不能直接 SELECT DB。测试环境的 synthetic records 不等于真实用户履历。

## Ownership and implementation map

| Area | 当前实现 | 尚未实现/限制 |
| --- | --- | --- |
| Core | Evidence、Opportunity、Job/Requirement、Capability、Project、Match/Gap、Fact、Resume、Application/Interview/Outcome 服务和存储 | 不代表所有实体都有完整 Web command UX |
| Context | 五类资产 compiler、immutable exact manifest、atomic audit | Me/Context 完整个性化配置与编辑尚缺 |
| Today | deterministic queue、精确面试时间恢复、frontend | canonical deadline 来源和 Investment 输入尚缺；快速收集/周回看未接入 |
| Capability | official release/personal overlay 分层、Inbox USER review、workspace | 不自动初始化真实官方图谱或认证个人 mastery |
| Market | BROAD on-read aggregation、TARGET bindings | legacy skill/topic authority mapping 未批准 |
| Resume | base/patch/revision、provenance-qualified user review、read API | PDF renderer/全流程编辑未实现 |
| History/Evidence | current Application 与 exact Outcome refs；Evidence metadata pagination/detail | 不下载 raw artifact，不把市场面经变成用户 Interview |
| Migration | no-link inventory、pinned safe reads、ArtifactStore integrity、archive/rehearsal/restore | 仅 preservation subset；structured business mapping/cutover 未完成 |
| Feishu | deterministic offline projection/schema/mapping | transport、credentials、sync/cursors/inbound commands 未实现 |
| Executor | L1 plan + canonical task lifecycle、L2 context preview | live CLI runner/results/L3 未实现 |

## Truth and storage

Career Core owns approved/new Harness business truth. Legacy remains historical evidence until
approved reconciliation and cutover. Artifact Store owns immutable bytes; Web/Feishu project.
Inference, scanning, archive, task completion and frequent appearances never grant fact/mastery authority.

AppPaths Windows default is `%LOCALAPPDATA%/AgentCareerHarness`; `ACH_DATA_DIR` overrides it.
One existing Data Root is reused. `career_harness.db` production database was not populated from
Legacy. Disposable rehearsal databases and their restore copies remain in the existing backups area.
No `LegacyJob`, `LegacyEvidence` or alternative Career Core was introduced.

## Current gaps and dependency order

1. Projects/Resume read clients `05913cb` are independently approved and merged at `12315f4`; richer workflows remain planned.
2. Resolve source identity/grades/question mapping/candidate gates before canonical structured data.
3. Broaden real-user read-model acceptance after approved records exist.
4. Feishu transport requires credential/destination permission and reviewed sync policy.
5. L2 execution requires separate runner/result contract plus explicit context/provider/budget.

Historical source documents are not changed into approval records. This map and v1.5 PRD report
implementation; neither grants production permission nor claims v1.4 product acceptance complete.
