# Roadmap

The phase ordering follows the authoritative PRD. Work may proceed in parallel only
where its gate and safety boundary are already satisfied.

## P0A - Legacy Agent Radar Closure

Owned by the legacy workspace. This repository treats that workspace as read-only
and consumes only approved snapshots or inventory metadata. No closure writes are
performed here.

## P0F - New Application Foundation

Current phase.

- Git repository and security exclusions
- Tauri 2 and React/TypeScript/Vite shell
- Python localhost API and health endpoint
- SQLite empty-schema bootstrap and migrations
- app-data/config/secret abstractions
- repeatable unit, integration, and contract tests

## P0B - Minimum Career Core and Migration

Current approval-free preparation only.

- typed domain boundaries and invariants
- command/revision/event/idempotency contracts
- LocalStepRunner interface and state model
- content-addressed artifact store foundation
- read-only legacy inventory and import manifest
- reconciliation model, migration runner, backup/restore preparation

Canonical cutover requires approved reconciliation and is not part of this goal.

## P0C - Feishu Staging Companion

Deferred. Requires relevant ADR gate. No production write is permitted.

## P0D - Desktop Read-only MVP

Deferred until P0F foundations are verified. It will expose Today, Radar, Discover,
Opportunity, and Evidence read models with limited low-risk commands.

## P1 - Career Intelligence and Resume

Do not start yet.

## P2 - Application, Interview, and Outcome

Do not start yet. Real browser form preparation and submission are explicitly out of
scope for the current goal.

## P3 - Platformization

Do not start yet. Plugin registry, multi-agent runtime, external workflow runtime,
and advanced memory require proven P0-P2 needs.

