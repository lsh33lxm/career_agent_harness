# Agent Career Harness v1.4 Architecture Map

**Observed repository:** commit `63ca32f` on 2026-09-18  
**Authoritative product direction:** `docs/prd/Agent_Career_Harness_PRD_v1.4_中文版.md`  
**Hard-constraint baseline:** `AGENT_CAREER_HARNESS_PRD_v1.2.md`  
**Contract version:** `v1.4-contract-0.2.0`

## Current architecture

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
| Project Evidence | MISSING | Generic Evidence exists; no Project, scope, scan or binding. |
| Target Market Evidence | MISSING | Market skeleton cannot distinguish target evidence. |
| Broad Market Trend | MISSING | Deferred beyond initial vertical slice. |
| Career History / Outcomes | PARTIAL | Outcome skeleton only; no history/query/provenance. |
| Context Compiler | MISSING | No relevance selector, compressor or assembler. |
| Context Manifest | MISSING | No invocation input/exclusion/model/capability audit record. |
| Discover | STUB | UI route and legacy enum value only. |
| Watchlist | LEGACY_CONFLICT | `WATCHING` is an Opportunity state; v1.4 requires a separate funnel stage. |
| Opportunity | PARTIAL | Typed state only; no admission confirmation, JD or repository. |
| Application | PARTIAL | Separation/submission authority enforced; no repository/API. |
| Suggested Priority | MISSING | Must be recomputable and explained. |
| User Priority | MISSING | Must be user-owned and never silently overwritten. |
| Today Action Queue | STUB | Static zero-count UI; no compiler/read model. |
| Official Capability Graph | MISSING | No node/relation/version storage. |
| Personal Capability Overlay | MISSING | No user-specific capability state. |
| Capability Ontology | MISSING | Requires versioned official graph and inbox gate. |
| Personal Capability State | MISSING | No multidimensional or derived state. |
| Evidence Binding | MISSING | Generic evidence references are not capability bindings. |
| Market Binding | MISSING | No target-opportunity requirement binding. |
| Investment State | MISSING | No explainable heuristic or user interest/cost inputs. |
| Capability Inbox | MISSING | Candidate nodes and accept/merge/ignore flow absent. |
| Capability Investment Planning | MISSING | P0 simple, explainable rule set required. |
| Match / Gap | MISSING | No frozen-input assessment or actionable gap groups. |
| Project Capability State | MISSING | Existing/understood/modified/extended/validated/resume-ready absent. |
| Project Enhancement Loop | MISSING | No gap-to-project-to-evidence chain. |
| Project Enhancement Task | MISSING | P0 L1 contract required. |
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
