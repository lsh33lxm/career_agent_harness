# Current Phase

PRD v1.4 Wave 1 is integrated. Opportunity, Capability, Project Evidence and Context persistence,
typed Capability/Project reads, the scope-safe scanner and the first real desktop projection are
complete. Canonical Evidence, Job/JobRequirement persistence and the pure evidence-aware Match/Gap
policy are complete; Wave 2 now advances to durable Match/Gap persistence and an exact input
resolver over frozen typed revisions.

# Current Goal

Build Match/Gap on exact JobRequirement, Capability, Opportunity, Evidence and Project revisions
before Resume and Outcome integration.

# Last Verified Commit

`e82d6cc` - `fix: validate gap capability on match read path`

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
- Integrated Capability, Opportunity, Project Evidence and Context Core contracts.
- Added typed Opportunity persistence, atomic command writes, independent priorities,
  read repository and authenticated Local API.
- Added additive Capability migration `0003` with separate official graph, candidate
  inbox, personal overlay, evidence/market binding and explainable investment records.
- Enforced immutable released graphs, authority allowlists, revision-preserving personal
  state, binding consistency and investment rule consistency at the SQLite boundary.
- Integrated the Opportunity desktop page with authenticated read/admission/priority APIs,
  Core-owned canonical ID generation, independent Suggested/User Priority projections and
  retry-safe mutation refresh behavior.
- Verified the Opportunity UI at desktop, 390 px and 320 px widths with no horizontal
  overflow or incoherent overlap; Vitest passed 16 tests and the Vite build passed.
- Added additive Project Evidence migration `0004` with revisioned scan scopes/manifests,
  immutable evidence, exact Capability evidence revisions, relational Project Capability basis
  rows and L1 enhancement tasks.
- Enforced deny-wins normalized paths, non-empty immutable manifests, evidence authority/review
  limits and atomic Project Capability aggregate writes at the SQLite boundary.
- Verified `0003 -> 0004 -> 0003 -> 0004`, Ruff, and backend `136 passed, 1 skipped`; the skip is
  the existing Windows symlink-permission limitation.
- Added additive Context Manifest migration `0005` with immutable ordered asset/knowledge refs,
  exact Project Evidence revisions, parent-last aggregate finalization and contract `0.2.0`.
- Context persistence stores only bounded audit metadata and hashes; it does not store task input,
  asset/knowledge payloads, assembled context, compiled prompts or fact-mutation authority.
- Verified `0004 -> 0005 -> 0004 -> 0005`, Ruff, and backend `151 passed, 1 skipped`.
- Added atomic Context compilation write/read integration: typed manifest, generic revision,
  `context.compiled` event and idempotency now share one transaction.
- Replay returns the first canonical manifest timestamp; compiler output is rebound to the exact
  request before persistence, and payload content cannot use generic audit rows as a storage path.
- Verified backend `159 passed, 1 skipped`, full Ruff lint, focused format and diff checks.
- Added typed Capability reads for exact/latest official graphs, candidate inbox, identity-scoped
  personal overlays, exact evidence bindings, target/broad market bindings and investment states.
- Added additive migration `0006` to reject candidate/capability identity drift across one
  `personal_state_id`; historical drift fails upgrade without rewriting data.
- Promoted exact `project_evidence_id` plus revision into the shared `EvidenceBinding` contract and
  removed the temporary repository-only read envelope.
- Added canonical Project/scope reads and a scope-safe local scanner: POSIX uses `openat`/`dir_fd`
  with no-follow handles; Windows rejects UNC/device/non-fixed drives and verifies reparse/final
  path containment while reading from the same handle.
- Independent reviews found no remaining P0/P1. Integration verification passed `192` tests with
  `3` known Windows symlink-permission skips; full Ruff passed.
- Added immutable Job revisions and versioned JobRequirements. AI/Agent proposals cannot review
  themselves; accepted requirements must pin an official capability and graph version.
- Added exact/latest Project Capability state, ordered basis and enhancement task repository reads;
  malformed aggregates fail loud and existing stable-identity triggers now have direct tests.
- Independent reviews found no P0/P1/P2 in either workstream. Combined integration verification
  passed `221` tests with `3` known Windows symlink-permission skips; full Ruff passed.
- Added immutable Evidence artifact/source/snapshot/reference persistence with exact provenance,
  credential/session rejection, typed reads and fail-loud malformed-data handling.
- Added additive migration `0008` and typed repositories for immutable Job revisions and versioned
  JobRequirements, preserving legacy Opportunity orphans while guarding future canonical refs.
- Added atomic Job/Requirement commands: typed rows, generic revision, DomainEvent and idempotency
  commit together; only USER commands can review proposals, and accepted mappings require exact
  official capability membership.
- Independent review found no P0/P1. Backend verification passed `237` tests with `3` known Windows
  symlink-permission skips; Ruff, format and diff checks passed.
- Added the pure evidence-aware Match/Gap policy over frozen exact inputs: COVERED requires both
  personal scope dimensions and qualified non-AI evidence per scope; AI_INFERRED, stale and
  unqualified evidence are excluded; Project Capability State contributes proximity only; dangling
  provenance and unreferenced inputs fail closed; output is deterministic under input reordering.
- Independent final review found no P0/P1; P2 test gaps (evidence-only coverage, rejected/superseded
  evidence, unreferenced inputs, mismatched personal state, full-input reordering) were added.
  Backend verification passed `252` tests with `3` known Windows symlink-permission skips; Ruff,
  format and diff checks passed.
- Added durable Match/Gap persistence (merge `b04d08e`): additive migration 0009 with immutable
  assessment/requirement-result/canonical-gap tables, typed reads, an atomic record service
  (typed rows + generic revision + `match.assessed` + idempotency in one transaction) and an exact
  Opportunity revision read. Independent review found one P1 (Opportunity JobRef binding) plus P2
  validation gaps; all fixed before merge. Backend verification passed `274` tests with `3` known
  Windows symlink-permission skips; Ruff and diff checks passed.
- Added the exact Match input resolver, assess orchestration and stored-manifest replay (merge
  `288ee30`): all inputs resolve through exact reads and fail loud on dangling or drifting
  provenance; replay re-runs the stored policy version against the stored manifest and never
  writes. Independent review found no P0/P1. Backend verification passed `292` tests with `3`
  known Windows symlink-permission skips; Ruff and diff checks passed.

# In Progress

- None active; the Match/Gap vertical (pure policy, durable persistence, resolver, replay) is
  integrated. Next: Project Enhancement linkage to canonical Gaps.

# Blocked

- None for P0F/P0B preparation.

# Needs User Approval

- All ADR-013 through ADR-016 decisions remain PROPOSED.
- Legacy source-of-truth reconciliation and canonical SQLite cutover.
- PRD open questions including retention, encryption, backup medium, final opaque ID
  format, and production integration choices.

# Next Safe Tasks

1. Link `ProjectEnhancementTask.target_gap_id` to canonical Gaps with write-path fail-loud
   validation, then wire the Gap → enhancement → evidence loop.
2. Add only the Project/Capability Local API projections required by the vertical loop.
3. Review whether `ProjectSourceManifest` should also pin an exact Project revision before schema
   expansion; current manifests already pin exact scope revision and immutable source entries.
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
