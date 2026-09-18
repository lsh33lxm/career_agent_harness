# Current Phase

PRD v1.4 Wave 0 is in progress: repository reconciliation, shared contract freeze,
additive migration planning, and test baseline stabilization.

# Current Goal

Establish a reviewable v1.4 integration baseline before scoped Wave 1 worktrees begin.

# Last Verified Commit

`01e2bbe` - `feat: commit opportunity truth atomically`

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
- Added OS-aware application data paths that keep ordinary artifacts, backups,
  browser sessions, and logs separate.
- Added a redacting SecretProvider boundary backed by environment injection; no
  secret values are persisted or logged.
- Added consistent SQLite online backup, artifact manifest/hash verification,
  integrity check, non-overwriting restore, and a full restore rehearsal test.
- Added typed Candidate, Market, Opportunity, Resume, Application, Interview, Prep,
  Outcome, Approval, Run, and Snapshot skeletons plus a repository protocol.
- Added executable invariants for Opportunity/Application separation,
  Prepared/Submitted separation, workflow/business state separation, user-only final
  approval, and TEST-to-PROD rejection.
- Generated the standard Tauri icon set from a deterministic project SVG, resolved
  Rust dependencies into `Cargo.lock`, passed `cargo check --locked`, and built the
  Windows debug executable with `--no-bundle`.

# In Progress

- Opportunity priority command/query API on the atomic persistence boundary.
- Capability, Project Evidence, and Context additive relational schema design.

# Blocked

- None for P0F/P0B preparation.

# Needs User Approval

- All ADR-013 through ADR-016 decisions remain PROPOSED.
- Legacy source-of-truth reconciliation and canonical SQLite cutover.
- PRD open questions including retention, encryption, backup medium, final opaque ID
  format, and production integration choices.

# Next Safe Tasks

1. Add atomic SuggestedPriority/UserPriority commands and Opportunity read repository.
2. Expose a typed localhost Opportunity read/mutation API with existing auth/CORS guarantees.
3. Add Capability, Project Evidence, and Context schemas in small additive migrations.
4. Continue awaiting user adjudication for destructive legacy cutover decisions.

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
npm --prefix apps/desktop exec -- tauri build --debug --no-bundle
```
