# Current Phase

P0F - New Application Foundation, with approval-free P0B migration preparation.

# Current Goal

FOUNDATION & MIGRATION READY.

# Last Verified Commit

`d529f64` - `chore: initialize agent career harness repository`

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

# In Progress

- React/TypeScript/Vite frontend and typed backend health connection.

# Blocked

- None for current foundation work.

# Needs User Approval

- All ADR-013 through ADR-016 decisions remain PROPOSED.
- Legacy source-of-truth reconciliation and canonical SQLite cutover.
- PRD open questions including retention, encryption, backup medium, final opaque ID
  format, and production integration choices.

# Next Safe Tasks

1. Bootstrap React/Vite frontend and health connectivity.
2. Add the minimal Tauri 2 shell if the existing toolchain validates.
3. Implement legacy read-only inventory, manifest, and reconciliation report.
4. Add backup/restore rehearsal for disposable foundation data.

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
