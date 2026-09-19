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
| W1-INT | Lead-owned shared schema/API integration | W1-* contracts | Lead | integration | IN_PROGRESS | High | Schemas, Context service, typed reads and scanner done; vertical Match/Gap integration remains. |
| W1-PROJ-READ | Project typed reads and scope-safe local scanner | W1-PROJ, 0004 | Subagent | project-read | DONE | High | Exact reads; scanner rejects scope, symlink/reparse and secret/session escapes. |
| W1-CAP-READ | Capability graph and personal overlay typed reads | W1-CAP, 0003 | Subagent | capability-read | DONE | Medium | Version-exact official/personal/market/investment queries preserve separation. |

## Wave 2 - Vertical career loop

| ID | Description | Dependencies | Owner | Worktree | Status | Risk | Definition of Done |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W2-MATCH | Evidence-aware Match/Gap and investment heuristic | W1-CAP/OPP/PROJ | Lead | integration | READY | Medium | Explainable factors and frozen inputs. |
| W2-RESUME | Resume Base/Patch/Revision integration | W1-PROJ, W2-MATCH | TBD | TBD | NOT_STARTED | High | Unverified claims cannot enter accepted patch. |
| W2-APP | Application/Outcome/history completion | W1-OPP, W2-RESUME | TBD | TBD | NOT_STARTED | High | Prepared/submitted and outcome authority tested. |
| W2-UI | Read APIs plus Opportunity/Project/Capability views | Integrated cores | TBD | TBD | NOT_STARTED | Medium | Real read models replace selected placeholders. |
| W2-OPP-UI | Opportunity API client and desktop page | Opportunity API | Subagent | opportunity-ui | DONE | Medium | Authenticated UI uses Core-owned IDs, preserves priority separation and passes responsive validation. |

## Wave 3+ deferred

Today dynamic queue, Capability Inbox UI, broad market trends, incremental scanning and optional
Claude/Codex CLI adapters are P1. L3 executor/worktree automation and advanced graph versioning are
P2. They do not begin until the P0 vertical loop is integrated and verified.
