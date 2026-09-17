# Current Phase

P0F - New Application Foundation, with approval-free P0B migration preparation.

# Current Goal

FOUNDATION & MIGRATION READY.

# Last Verified Commit

None yet. Repository initialization is in progress.

# Completed

- Confirmed the new repository path.
- Read the authoritative PRD v1.2 in full.
- Confirmed the new repository initially contained only the PRD.
- Confirmed the legacy Agent Radar workspace is outside this repository and is not
  a Git repository.
- Confirmed 38 source Project Cards exist in the read-only records directory.
- Confirmed local Node, npm, Python, Rust, and Cargo toolchains are available.

# In Progress

- Repository security baseline and durable project documentation.
- Architecture, migration, ADR, and research indexes.

# Blocked

- None for current foundation work.

# Needs User Approval

- All ADR-013 through ADR-016 decisions remain PROPOSED.
- Legacy source-of-truth reconciliation and canonical SQLite cutover.
- PRD open questions including retention, encryption, backup medium, final opaque ID
  format, and production integration choices.

# Next Safe Tasks

1. Verify and commit the documentation/security baseline.
2. Bootstrap Python API, SQLite migrations, and core contracts with tests.
3. Bootstrap React/Vite frontend and health connectivity.
4. Add the minimal Tauri 2 shell if the existing toolchain validates.
5. Implement legacy read-only inventory, manifest, and reconciliation report.

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

