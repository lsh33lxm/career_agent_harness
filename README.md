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

## Backend Development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
$env:ACH_LAUNCH_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -m career_harness --token $env:ACH_LAUNCH_TOKEN
```

The API binds only to `127.0.0.1`. Call `GET /health` with
`Authorization: Bearer <launch-token>`. Do not persist the generated token.

Run backend checks with:

```powershell
.\.venv\Scripts\ruff.exe check backend tests migrations
.\.venv\Scripts\python.exe -m pytest -q
```

## Frontend Development

```powershell
npm install
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8765'
$env:VITE_LAUNCH_TOKEN = $env:ACH_LAUNCH_TOKEN
npm run dev
```

Open `http://127.0.0.1:5173`. The P0 shell includes all planned primary routes and
reports authenticated sidecar health. Search and Capture remain visibly disabled
until their Core commands exist.

```powershell
npm test
npm run build
cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml
```

## Legacy Read-only Inventory

```powershell
.\.venv\Scripts\python.exe -m importers.agent_radar inventory `
  --source 'D:\0.小红书投稿\小红书稿\9.15 三期\agent_rader' `
  --output '.\LEGACY_IMPORT_MANIFEST.json' `
  --verify
.\.venv\Scripts\python.exe -m importers.agent_radar reconcile `
  --manifest '.\LEGACY_IMPORT_MANIFEST.json' `
  --output '.\LEGACY_RECONCILIATION_REPORT.md'
```

The importer refuses outputs inside the source workspace, does not follow links, and
never approves a candidate identity. Generated manifest/report files are ignored by
Git because their path inventory may contain private historical metadata.
