# Agent Career Harness

![观复今日工作台](assets/readme/guanfu-today.png)

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

## Offline Demo and Job Seed

The repository contains a normalized offline job seed under `data/jobs/`. The
current manifest version is `legacy-jobs-v2` with 492 release-eligible records
from the read-only Agent Radar audit. The source ledger authorization attestation
covers the full source batch; no records are kept local-only in this release seed.
The seed contains job
metadata and provenance links, not screenshots, raw captures, credentials,
personal resumes, runtime databases, or logs.

The packaged seed is read through the existing Opportunity Radar pipeline. Demo
Mode does not require an API key or external network and does not depend on the
legacy project path. User admission, resume patches, application state, and any
communication draft remain separate user-controlled actions.

## 求职沟通邮箱

可在桌面端保存 IMAP 账户的非敏感配置，密码只进入系统凭据管理器。连接测试、指定文件夹读取和邮件关联都必须由用户主动执行；观复只保存邮件摘要，不自动轮询、不自动发信、不批量发送。

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
npm --prefix apps/desktop exec -- tauri build --debug --no-bundle
```

## Windows Desktop Packaging

The Tauri application owns the packaged Python sidecar lifecycle. Each launch selects a
free loopback port, creates an in-memory token, injects the connection configuration into
the webview, and terminates the complete PyInstaller process tree when the desktop window
closes. Runtime data persists under `%LOCALAPPDATA%\AgentCareerHarness` unless
`ACH_DATA_DIR` is set. Sidecar diagnostics are written to
`<data-root>\logs\desktop-sidecar.log`; the launch token is never written to that log or
the process command line.

Build the sidecar and NSIS installer with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop-build.lock
.\scripts\build_desktop_sidecar.ps1 -Python .\.venv\Scripts\python.exe
npm --prefix apps/desktop exec -- tauri build
```

The installer is generated at
`apps\desktop\src-tauri\target\release\bundle\nsis\Agent Career Harness_0.1.0_x64-setup.exe`.
The sidecar executable is generated locally under `apps\desktop\src-tauri\binaries` and
is excluded from Git.

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

## Demo mode and job data audit

The desktop shell can be opened without credentials in an explicit offline demo
mode by setting `VITE_DEMO_MODE=true`. It shows a Chinese demo banner and never
connects to a model provider or external platform. Search the approved packaged
seed through `/api/v1/jobs/packaged-seed-search`.

Run the audit after receiving the real local database path:

```powershell
python scripts/audit_job_db.py "D:\真实\岗位库.db" --output docs/data-audit.md
```

## Windows Private Beta

Build the sidecar and NSIS package with the commands in the Windows packaging
section. Install into a disposable Windows directory and set an isolated
`ACH_DATA_DIR` for verification. This project does not automatically submit jobs,
send email, or perform batch external actions; final decisions remain with the
user. The Desktop Verification Gate v0.1 is currently **NO-GO** because the real
Resume Review browser click-through, complete screenshots, and Playwright teardown
are not yet complete. No stable release is implied by the current build.
