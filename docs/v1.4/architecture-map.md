# Agent Career Harness v1.4 Architecture Map

**Observed repository:** integration commit `62f1ce8` on 2026-09-20
**Authoritative product direction:** `docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md`  
**Hard-constraint baseline:** `AGENT_CAREER_HARNESS_PRD_v1.2.md`  
**Contract version:** `v1.4-contract-0.14.1` (Today Interview inputs frozen; implementation in flight)

## Integrated capability workspace (2026-09-20)

Contract `0.13.0` / D-023 is implemented by `ae39eb6` + `e076daf`, merge `62f1ce8`.
`CapabilityRepository` -> pure Core workspace assembler -> read-only service -> authenticated
`GET /api/v1/capabilities/{candidate_id}` -> desktop `/capabilities`. Explicit candidate identity
and exact optional graph version preserve official/personal/evidence/TARGET/BROAD/proposal boundaries.
No migration, canonical write or client business ranking was added. Full backend: 403 passed,
3 skipped; frontend: 27 passed/build; recovery review APPROVE with no P0/P1/P2/P3.

The foundation diagrams and gap inventory below describe the original reconnaissance baseline;
`progress.md` and `refactor-plan.md` track subsequent completed slices.

## Foundation architecture (historical reconnaissance)

```text
React/Vite UI (mostly placeholders)
        |
        | authenticated REST/JSON; only GET /health exists
        v
FastAPI local service
        |
        +-- CommandService -> generic entity_state/entity_revision/domain_event/outbox
        +-- Evidence Pydantic contracts (not persisted)
        +-- lifecycle skeletons (not persisted through domain repositories)
        +-- ArtifactStore / backup / AppPaths (not wired into app startup)
        `-- LocalStepRunner (sequential execution contract)

Tauri shell: window only; no sidecar lifecycle/config injection
Legacy Agent Radar: read-only inventory/reconciliation importer only
```

The current repository is a sound P0 foundation, not a completed career product. SQLite is
canonical for newly created Harness records only. It is not canonical for legacy Agent Radar
history before approved reconciliation and cutover.

## Runtime ownership map

| Area | Current implementation | v1.4 target owner |
| --- | --- | --- |
| Frontend | React routes, health/offline state | Client/projection through typed Local API |
| Desktop shell | Minimal Tauri builder | Process/window/sidecar lifecycle only |
| Backend | FastAPI health endpoint | Application services and typed command/query API |
| Career Core | Evidence types, lifecycle skeletons, command substrate | Canonical business truth and policy |
| Database | Generic revision/event substrate | Relational domain records plus revision/audit substrate |
| Services | `CommandService` only | Use-case orchestration; no truth owned by adapters |
| Repositories | Protocol/implementation contract being aligned | Typed per-domain repositories |
| Adapters/workers | Empty packages | Replaceable capability providers and side-effect executors |
| Browser/LLM/Feishu | Not implemented | Explicit adapters; proposal/projection only |
| Resume | Empty entity skeleton | Base -> Patch proposal -> review -> Revision -> Render |
| Evidence | Typed in memory; ArtifactStore on disk | Persisted provenance and explicit promotion |
| Opportunity/Application | Lifecycle skeletons | Separate funnel records and user-gated transitions |
| Project/Context/Capability | Missing | New P0 domain slices described below |
| Audit | Domain event rows only | Queryable event/decision/approval/context manifests |

## Target architecture

```text
Desktop / future Feishu projection
              |
              v
Typed Local API (commands + read models)
              |
              v
Small Stable Career Core
  Personal Context | Career State | Project Evidence
  Target/Broad Market Evidence | Career History/Outcomes
  Evidence promotion | Capability graph/overlay | Resume truth
              |
              +--> Context Compiler --> Context Manifest --> model adapter
              +--> Career Reasoning --> proposals/actions (never silent truth)
              +--> Enhancement Task --> Manual Executor (P0 L1)
              |
              v
SQLite relational domain tables + revision/event/idempotency/outbox
              |
              v
Local Artifact Store and isolated session/extension/reference directories
```

## PRD to repository gap map

| v1.4 capability | Status | Repository evidence / required change |
| --- | --- | --- |
| Personal Context | MISSING | Candidate skeleton has no context facts/preferences/goals. |
| Career State | PARTIAL | Opportunity/Application/Outcome skeletons only. |
| Project Evidence | PARTIAL | Core/schema, exact reads and scope-safe scanner exist; write service/API remain. |
| Target Market Evidence | PARTIAL | Target MarketBinding exists; canonical versioned JobRequirement is the next prerequisite. |
| Broad Market Trend | EXISTS | Deterministic on-read aggregation over BROAD MarketBindings; merge `c6efb8b`, zero canonical writes. |
| Career History / Outcomes | PARTIAL | Outcome skeleton only; no history/query/provenance. |
| Context Compiler | EXISTS | Deterministic five-asset compiler and atomic audit write/read exist; advanced compression remains deferred. |
| Context Manifest | EXISTS | Immutable metadata-only 0005 schema and atomic service are integrated. |
| Discover | STUB | UI route and legacy enum value only. |
| Watchlist | PARTIAL | Separate typed/persisted record exists; compatibility `WATCHING` enum remains. |
| Opportunity | PARTIAL | User-gated admission, persistence/API and priority exist; canonical Job content is missing. |
| Application | PARTIAL | Separation/submission authority enforced; no repository/API. |
| Suggested Priority | EXISTS | Typed independent persisted projection with frozen input refs. |
| User Priority | EXISTS | User-only typed persistence is independent from Suggested Priority. |
| Today Action Queue | STUB | Static zero-count UI; no compiler/read model. |
| Official Capability Graph | EXISTS | Versioned immutable relational graph and exact/latest reads exist. |
| Personal Capability Overlay | EXISTS | Revisioned personal state is separate and identity-stable. |
| Capability Ontology | PARTIAL | Official graph/candidate inbox exist; publishing service remains. |
| Personal Capability State | EXISTS | Multidimensional state, evidence binding and derived status exist. |
| Evidence Binding | EXISTS | Capability bindings pin exact personal and Project Evidence revisions. |
| Market Binding | PARTIAL | Target/broad separation exists; target requirement revisions are not yet canonical. |
| Investment State | PARTIAL | Explainable stored factors exist, but canonical factor derivation is not implemented. |
| Capability Inbox | PARTIAL | Candidate/status contract and reads exist; review write service remains. |
| Capability Investment Planning | PARTIAL | Deterministic scoring exists; trustworthy target-input derivation remains. |
| Match / Gap | MISSING | Contract 0.3.0 frozen; canonical JobRequirement/persistence is the blocking prerequisite. |
| Project Capability State | PARTIAL | Typed relational state/basis exist; exact read repository is next. |
| Project Enhancement Loop | PARTIAL | L1 task contract/schema exist; canonical Gap and orchestration remain. |
| Project Enhancement Task | PARTIAL | P0 L1 contract/schema exist; repository/service remain. |
| Project Enhancement Executor | STUB | LocalStepRunner is not the executor abstraction. |
| Resume Base | MISSING | Existing `Resume` is an empty skeleton. |
| Resume Patch | MISSING | No evidence-linked proposal/review contract. |
| Resume Revision | MISSING | Generic revision substrate only. |
| Career Reasoning | MISSING | No decision record or recommendation service. |

## Legacy to v1.4 mapping

| Legacy/current concept | v1.4 treatment |
| --- | --- |
| Generic `entity_state` JSON | Compatibility substrate; do not add new domain blobs indefinitely. |
| `OpportunityState.WATCHING` | Preserve for compatibility, migrate to `WatchlistItem` before removal. |
| Candidate skeleton | Split into Personal Context and evidence-backed Career Facts. |
| Market skeleton | Split Target Market Evidence from Broad Market Trend. |
| Generic `Resume` | Replace incrementally with ResumeBase/Patch/Revision/Render. |
| DomainEvent row | Retain shared audit/event envelope; add domain-specific payload contracts. |
| Agent Radar files | Read-only source evidence; never direct Core truth. |
| Static Today page | Replace with read-only Dynamic Career Action Queue projection after core slices. |

## Dependency order

```text
shared IDs/evidence/event/ownership contracts
    -> relational migration policy
    -> capability + opportunity + project + context cores
    -> match/gap and L1 enhancement
    -> resume/application/outcome vertical slice
    -> Today/read APIs and UI
    -> optional adapters/executors
```
