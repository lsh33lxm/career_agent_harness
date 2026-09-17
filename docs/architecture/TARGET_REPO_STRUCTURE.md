# Target Repository Structure

This is the structure being implemented, not an abstract package wish list.

```text
agent-career-harness/
|-- apps/desktop/               React/Vite UI and Tauri lifecycle shell
|   |-- src/app/                router, layout, error/loading boundaries
|   |-- src/pages/              P0 route placeholders
|   |-- src/api/                typed localhost API client
|   `-- src-tauri/              minimal Rust lifecycle/capability boundary
|-- backend/career_harness/
|   |-- api/                    FastAPI routes, auth/origin boundary
|   |-- core/                   domain types, commands, revisions, events
|   |-- workflows/              LocalStepRunner contracts
|   |-- adapters/               typed replaceable external ports
|   |-- workers/                future high-cost/side-effect workers
|   |-- db/                     SQLAlchemy models/session/bootstrap
|   `-- services/               application orchestration
|-- importers/agent_radar/      read-only inventory and reconciliation
|-- migrations/                 Alembic migration environment and revisions
|-- schemas/                    portable JSON/data contracts
|-- research/project_cards/     index of read-only engineering references
|-- research/product_cards/     product journey reference templates
|-- docs/architecture/          executable system boundaries
|-- docs/adr/                   proposed and approved decision records
|-- docs/migration/             inventory, reconciliation, cutover plans
|-- tests/unit/                 pure domain behavior
|-- tests/integration/          API, database, and importer behavior
|-- tests/contract/             adapter and cross-boundary contracts
`-- scripts/                    bounded developer/verification commands
```

## Ownership rules

- Frontend uses Local API commands and never opens SQLite directly.
- Tauri owns process/window/native lifecycle only; business logic stays in Python.
- Core owns business truth; workers and adapters propose or project changes.
- Importers cannot write beneath the configured legacy root.
- Runtime databases, artifacts, credentials, personal material, and generated
  manifests are ignored by Git.

