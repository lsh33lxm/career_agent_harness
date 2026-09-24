# System Architecture

**Status:** P0F/P0B implementation baseline, subject to proposed ADR approval.

## Runtime topology

```text
Tauri 2 desktop process
  |-- owns window, sidecar lifecycle, native dialogs, capabilities
  `-- loads React/TypeScript/Vite UI
          |
          | REST/JSON, 127.0.0.1, random port, ephemeral launch token
          v
Python FastAPI sidecar
  |-- commands and query endpoints
  |-- Career Core policies and revisions
  |-- LocalStepRunner
  |-- adapter ports and workers
  |-- SQLite transactions + transactional outbox
  `-- content-addressed artifact store
          |
          | explicit typed adapters
          v
Playwright browser worker / parsers / model provider / renderer / Feishu companion
```

Development may use a fixed localhost port and explicit development token. Release
packaging must allocate a random port and inject a per-launch token. The API must
never bind `0.0.0.0`.

## Truth and transaction boundary

Career Core is the only business truth owner. A command validates
`expected_revision` and `idempotency_key`, then commits current state, an immutable
revision, a DomainEvent, and any OutboxMessage in one SQLite transaction. This is
not full event sourcing: current state and immutable revisions remain primary.

SQLite is canonical only for newly created Harness data during foundation work. It
does not become canonical for legacy Agent Radar history before approved inventory,
reconciliation, import manifest, verification, backup/restore rehearsal, and
cutover.

## Evidence boundary

Capture and parsing produce Artifact, SourceSnapshot, EvidenceRef, and
ExtractedClaim records. Only an explicit policy/user review command may promote an
accepted claim into a separately typed Fact revision. Signals, decisions, and
outcomes keep their own provenance and cannot be silently converted into facts.

## External side effects

Workers consume explicit jobs and report results. Browser and Feishu operations use
allowlisted capabilities, idempotency records, audit events, and human approval
boundaries. Credential/session data uses separate storage and never enters the
ordinary artifact store, model input, or Feishu.

## Failure model

- UI failure cannot partially commit a Core transaction.
- Worker/adapter failure cannot mutate canonical state outside a command.
- Outbox delivery retries are idempotent and cannot roll back Core state.
- Revision conflicts are visible and require retry/review, never last-write-wins.
- Sidecar health is observable through `/health`; crash recovery belongs to Tauri.

