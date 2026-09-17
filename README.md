# Agent Career Harness

Agent Career Harness is a local-first desktop career workspace. It keeps evidence,
candidate facts, decisions, approvals, and outcomes auditable while leaving legal,
identity, work-authorization, and final application submission decisions with the
user.

## Authority

[`AGENT_CAREER_HARNESS_PRD_v1.2.md`](AGENT_CAREER_HARNESS_PRD_v1.2.md) is the
authoritative product and implementation baseline. Repository documentation may
index or explain it, but does not replace it.

Core invariants:

- Evidence, Fact, Signal, Decision, and Outcome are distinct concepts.
- An ExtractedClaim is not a verified Fact.
- Workflow state is not business state.
- An Opportunity is not an Application; Prepared is not Submitted.
- Agents, adapters, the desktop UI, and Feishu do not own truth.
- The legacy Agent Radar workspace remains read-only until approved cutover.

## Target Stack

- Tauri 2 desktop lifecycle and native boundary
- React, TypeScript, and Vite frontend
- Python local API sidecar bound to `127.0.0.1`
- SQLite plus a local content-addressed artifact store
- Playwright browser worker with human-in-the-loop controls
- Feishu companion adapter

## Repository Map

- `apps/desktop/`: frontend and Tauri shell
- `backend/career_harness/`: local API, core, workflows, adapters, and services
- `importers/agent_radar/`: read-only legacy inventory and reconciliation
- `migrations/`: versioned SQLite migrations
- `schemas/`: shared data contracts
- `docs/`: architecture, ADR, migration, and PRD indexes
- `research/`: engineering and product reference cards
- `tests/`: unit, integration, and contract tests

## Current State

See [`STATUS.md`](STATUS.md) for verified progress, blockers, and commands. This
repository is in P0F/P0B foundation work; it is not a canonical cutover of legacy
Agent Radar data and it performs no production Feishu or ATS writes.

