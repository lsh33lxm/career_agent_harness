# Agent Career Harness v1.4 Refactor Plan

Statuses: `NOT_STARTED`, `READY`, `IN_PROGRESS`, `IN_REVIEW`, `BLOCKED`, `DONE`.

## Wave 0 - Reconciliation and contract freeze

| ID | Description | Dependencies | Owner | Worktree | Status | Risk | Definition of Done |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W0-01 | Read PRDs/Handoff and map repository | None | Lead | integration | DONE | Low | Architecture and gap map grounded in code. |
| W0-02 | Freeze shared v1.4 semantic contracts | W0-01 | Lead | integration | DONE | High | Contracts versioned; ownership/invariants explicit. |
| W0-03 | Align command repository/service contract | W0-01 | Lead | integration | DONE | Medium | Typed result, explicit event type, tests pass. |
| W0-04 | Define additive migration strategy | W0-02 | Lead | integration | DONE | High | No cutover/data-loss assumptions; schema ownership clear. |
| W0-05 | Establish full test baseline | None | Lead | integration | DONE | Low | Python tests and Ruff pass; frontend/Rust baseline recorded. |
| W0-06 | Create scoped Wave 1 worktrees/prompts | W0-02..04 | Lead | integration | DONE | Medium | Ownership has no shared-schema overlap. |

## Wave 1 - P0 domain cores

| ID | Description | Dependencies | Owner | Worktree | Status | Risk | Definition of Done |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W1-CAP | Capability core and personal overlay | W0-02 | Subagent | capability | DONE | High | Models/services/tests enforce official/personal separation. |
| W1-OPP | Watchlist/Opportunity/Priority core | W0-02 | Subagent | opportunity | DONE | High | User-gated admission and priority independence tested. |
| W1-PROJ | Project scope/evidence/enhancement L1 core | W0-02 | Subagent | project-evidence | DONE | High | Deny-wins scope and evidence candidates tested. |
| W1-CTX | Five-asset Context Compiler basic | W0-02, domain read ports | Subagent | context | DONE | Medium | Relevance selection and ContextManifest tests pass. |
| W1-INT | Lead-owned shared schema/API integration | W1-* contracts | Lead | integration | DONE | High | Schemas, Context service, typed reads, scanner and vertical Match/Gap integration are tested. |
| W1-PROJ-READ | Project typed reads and scope-safe local scanner | W1-PROJ, 0004 | Subagent | project-read | DONE | High | Exact reads; scanner rejects scope, symlink/reparse and secret/session escapes. |
| W1-CAP-READ | Capability graph and personal overlay typed reads | W1-CAP, 0003 | Subagent | capability-read | DONE | Medium | Version-exact official/personal/market/investment queries preserve separation. |
| W1-PROJ-STATE-READ | Project capability state/basis and enhancement task reads | W1-PROJ, 0004 | Subagent | project-state-read | DONE | Medium | Exact/latest aggregates retain basis revisions, finalization time and stable ordering. |

## Wave 2 - Vertical career loop

| ID | Description | Dependencies | Owner | Worktree | Status | Risk | Definition of Done |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W2-JOB | Versioned Job/accepted JobRequirement domain prerequisite | Evidence, Capability Graph | Subagent | job-requirement | DONE | High | AI proposals stay separate; accepted requirements pin evidence and official graph revision. |
| W2-JOB-PERSIST | Additive Job/JobRequirement schema, typed repository and atomic promotion service | W2-JOB, 0006 | Lead | integration | DONE | High | Exact evidence/graph refs, authority checks, generic revision/event/idempotency and legacy Opportunity compatibility are tested. |
| W2-MATCH | Evidence-aware Match/Gap pure policy | W2-JOB-PERSIST, W1-PROJ-STATE-READ | Lead | integration | DONE | Medium | Explainable three-way assessment with frozen exact inputs; independent final review passed. |
| W2-MATCH-PERSIST | Durable Match/Gap persistence (schema, typed reads, atomic record) | W2-MATCH | Subagent | match-persistence | DONE | High | Contract `0.4.0`; additive 0009 rehearsal passed; P1/P2 review fixes merged. |
| W2-MATCH-RESOLVER | Exact Match input resolver, assess orchestration and replay | W2-MATCH-PERSIST | Subagent | match-resolver | DONE | High | Exact reads only; replay from stored manifest fails loud on drift. |
| W2-ENHANCE-LINK | Enhancement task write path linked to canonical Gaps | W2-MATCH-RESOLVER | Subagent | enhancement-link | DONE | Medium | Contract `0.4.1`; dangling gap and capability mismatch fail loud. |
| W2-FACT | CareerFact/FactProposal domain and promotion path | Evidence, Capability bindings | Subagent | fact-promotion | DONE | High | AI-inferred material cannot become a Fact; patch consumers can resolve qualified fact refs. |
| W2-RESUME | Resume Base/Patch/Revision integration | W1-PROJ, W2-MATCH, W2-FACT | Subagent | resume-core | DONE | High | Exact qualified provenance, USER review and immutable content-hashed revisions tested. |
| W2-APP-CONTRACT | Freeze Application submission and Outcome authority contract | W1-OPP, W2-RESUME | Lead | integration | DONE | High | Contract `0.7.0`; exact refs, user authority, sensitive-data and no-ATS boundaries explicit. |
| W2-APP | Application/Outcome/history completion | W2-APP-CONTRACT | Lead | integration | DONE | High | Prepared/submitted separation, exact refs, receipt/user authority, immutable Outcome and atomic persistence tested. |
| W2-UI | Read APIs plus Opportunity/Project/Capability views | Integrated cores | Lead | integration | IN_PROGRESS | Medium | Today, Opportunity and Capability views consume Core APIs; remaining primary views still need projections. |
| W2-CAREER-READ | Authenticated Resume/Application/Outcome reads | W2-RESUME, W2-APP | Lead | integration | DONE | Medium | Exact/latest read-only projections pass auth, 404 and no-write-route tests. |
| W2-OPP-UI | Opportunity API client and desktop page | Opportunity API | Subagent | opportunity-ui | DONE | Medium | Authenticated UI uses Core-owned IDs, preserves priority separation and passes responsive validation. |
| W2-CAP-VIZ | Candidate-scoped Capability Workspace read API and visualization | W1-CAP-READ, Broad Market Trend | Subagent | capability-visualization | DONE | Medium | Merge `62f1ce8`; final recovery review APPROVE; full 403 passed, 3 skipped; frontend 27 passed/build and browser fixture checks passed. |
| W2-TODAY-INTERVIEW | Exact Interview schedule inputs for existing Today interview-stage items | Today read model, Interview records | Subagent | today-interview | DONE | Medium | Merge `dc85365`; contract `0.14.1` / D-024; review APPROVE; full 440 passed, 3 skipped. |

| W2-L2-PREP | Exact-context tools-disabled CLI invocation preparation | Enhancement L1, exact project scope/manifest reads | Subagent | l2-analysis-prep | DONE | Medium | Merge `9101085`; contract 0.15.0 / D-025; final review APPROVE; full 534 passed, 3 skipped; no execution. |
| W2-INBOX-CLIENT | Capability Inbox authenticated reads and explicit user review UI | Inbox Core, Capability Workspace | Subagent | capability-inbox-client | DONE | Medium | Merge `6ba054d`; contract 0.16.0 / D-026; final APPROVE; full 551 passed, 3 skipped; frontend 39 passed/build and browser E2E. |
| W2-L1-OFFLINE | Section 29.7 offline L1 acceptance | L1 executor, ProjectService | Subagent | l1-offline-acceptance | DONE | Low | `aa08afa`, merge `3626994`; final APPROVE; full 552 passed, 3 skipped. |
| W2-L2-RUN | Bounded CLI execution and proposal result handling | W2-L2-PREP, explicit context/provider/budget approval | Lead | unassigned | BLOCKED | High | Runner contract/review and explicit real-inference authorization required; not implemented. |

## P1 and P2 status

Today dynamic queue and UI adapter, Capability Inbox review, broad market trends and incremental
scanning, Capability Workspace visualization and Inbox accept/ignore UI are implemented. Optional
CLI execution and dynamic SuggestedPriority policy remain P1; L2 invocation preparation is done. The P0 end-to-end acceptance fixture is integrated; the next
READY slice must be selected from the remaining dependency graph and receive a contract freeze.

L3 executor/worktree automation, advanced graph versioning and outcome-driven recommendation are
P2 and remain deferred.
