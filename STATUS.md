# Current Phase

P0F - New Application Foundation, with approval-free P0B migration preparation.

# Current Goal

FOUNDATION & MIGRATION READY.

# Last Verified Commit

`ae6a192` - `feat: bootstrap desktop frontend and tauri shell`

# Completed

- Confirmed the new repository path.
- Read the authoritative PRD v1.2 in full.
- Confirmed the new repository initially contained only the PRD.
- Confirmed the legacy Agent Radar workspace is outside this repository and is not
  a Git repository.
- Confirmed 38 source Project Cards exist in the read-only records directory.
- Confirmed local Node, npm, Python, Rust, and Cargo toolchains are available.
- Established security exclusions, architecture/migration documents, proposed
  ADR-013 through ADR-016, and research indexes.
- Added authenticated localhost-only FastAPI `/health` endpoint.
- Added Alembic/SQLite fresh bootstrap with current state, immutable revision,
  DomainEvent, idempotency, transactional outbox, and migration mismatch tables.
- Added typed Evidence/ExtractedClaim/Fact, Command/revision, 11 Core module
  boundaries, LocalStepRunner contract, and content-addressed Artifact Store.
- Verified atomic command commit and idempotent replay behavior.
- Backend verification: Ruff passed; pytest passed 14 tests on Python 3.13.12.
- Added React/TypeScript/Vite App Shell with Today, Discover, Opportunities, Resume,
  Applications, Interviews, Prep, Insights, Evidence, and Settings routes.
- Added typed bearer-authenticated frontend health client, loading/offline states,
  error boundary, responsive navigation, and disabled future controls.
- Fixed authenticated CORS preflight handling after real browser integration found
  that `OPTIONS /health` was incorrectly rejected.
- Added a minimal Tauri 2 shell and restrictive default capability/CSP boundary.
- Frontend verification: Vitest passed 4 tests, Vite production build passed, npm
  audit found 0 vulnerabilities, and browser verification displayed `Core 0.1.0`.
- Added a read-only Agent Radar importer with no-link traversal, streaming SHA-256,
  workbook structural metadata, output-boundary guards, and post-scan verification.
- Added typed candidate manifest and reconciliation schemas. Identity mappings remain
  null, approved entities remain empty, and conflict dispositions default explicitly
  to `deferred`.
- Real legacy inventory verified 2,210 files (360,355,195 bytes), 286 snapshot
  candidates, and 11 workbooks without observed source metadata changes. Generated
  reconciliation contains 332 deferred candidate records.

# In Progress

- Consistent backup/restore rehearsal and app-data/config foundation.

# Blocked

- Tauri `cargo check` could not complete because crates.io index retrieval stalled;
  offline resolution reports missing crate `jsonptr`. Rust 1.98 and Cargo 1.98 are
  installed, so retry dependency resolution when network access is responsive.

# Needs User Approval

- All ADR-013 through ADR-016 decisions remain PROPOSED.
- Legacy source-of-truth reconciliation and canonical SQLite cutover.
- PRD open questions including retention, encryption, backup medium, final opaque ID
  format, and production integration choices.

# Next Safe Tasks

1. Add backup/restore rehearsal for disposable foundation data.
2. Add app-data path and secret-provider abstractions.
3. Retry Tauri dependency resolution and `cargo check`.

# Do Not Start Yet

- P1/P2 features, real ATS actions, final submission, or legal/identity automation.
- Production Feishu writes or canonical legacy cutover.
- Playwright installation or browser automation.
- Multi-agent runtime, plugin marketplace, or external workflow engine.
- Large global/system toolchain installation.

# Verification Commands

```powershell
git status --short --branch
python -m pytest
npm --prefix apps/desktop test
npm --prefix apps/desktop run build
cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml
```
