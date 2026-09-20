# v1.4 Progress

| Work item | Status | Last update | Evidence |
| --- | --- | --- | --- |
| Repository reconnaissance | DONE | 2026-09-18 | `architecture-map.md`; baseline commands run. |
| PRD/Handoff version control | DONE | 2026-09-18 | `main` commit `63ca32f`. |
| Integration branch/worktree | DONE | 2026-09-18 | `refactor/v1.4-integration`. |
| Shared contract freeze | DONE | 2026-09-19 | Wave 2 prerequisite contract `0.3.0`; JobRequirement and frozen Match boundaries. |
| Repository contract alignment | DONE | 2026-09-18 | `32 passed, 1 skipped`; Ruff passed. |
| Additive migration strategy | DONE | 2026-09-18 | `migration-plan.md`; schema unchanged. |
| Wave 1 decomposition/prompts | DONE | 2026-09-18 | `f98faf6`; four prompts, three active worktrees. |
| Wave 1 domain contracts | DONE | 2026-09-18 | Capability, Opportunity, Project Evidence and Context integrated. |
| Wave 1 persistence/integration | DONE | 2026-09-19 | Schemas, Context service, Capability/Project reads and safe scanner are integrated. |
| Opportunity typed persistence | DONE | 2026-09-18 | `3f102f0`; 0002 migration, ORM parity, upgrade/downgrade tests. |
| Atomic Opportunity command path | DONE | 2026-09-18 | `01e2bbe`; typed/generic truth, event and idempotency share one transaction. |
| Opportunity Priority/read repository | DONE | 2026-09-18 | `878d222`; independent priorities and aggregate revisions tested. |
| Opportunity Local API/runtime | DONE | 2026-09-18 | `d1004b2`; auth, idempotency, conflict redaction and bootstrap tested. |
| Capability typed persistence | DONE | 2026-09-18 | `2b7901d`; additive 0003, immutable graph and overlay/binding constraints. |
| Opportunity desktop UI | DONE | 2026-09-18 | `f888f9a`, `c990589`, merge `f37b92b`, layout fix `0cee6c6`; 16 tests/build and desktop/390/320 visual checks passed. |
| Project Evidence typed persistence | DONE | 2026-09-19 | `158547b`; additive 0004, atomic relational basis, authority/scope and upgrade/downgrade tests. |
| Context Manifest typed persistence | DONE | 2026-09-19 | `95d3df6`; additive 0005, ordered immutable refs and metadata-only privacy boundary. |
| Context Manifest atomic service/read | DONE | 2026-09-19 | `6ca47cc`; one transaction, canonical replay, exact ordered readback and compiler-output binding. |
| Project typed reads / safe scanner | DONE | 2026-09-19 | `116fd50`, security fix `f3cfd9e`, merge `44a3e00`; handle-anchored scope enforcement. |
| Capability typed read repository | DONE | 2026-09-19 | `1615581`, `3c2d18c`, merge `7e7dfa5`; Lead guard/contract fix `61b5a4f`. |
| Project capability/task typed reads | DONE | 2026-09-19 | `3cb8d5f`, merge `e1182ab`; exact/latest aggregate reads and fail-loud reconstruction. |
| Versioned Job/JobRequirement core | DONE | 2026-09-19 | `deadc25`, merge `7728282`; proposal/review authority and exact official mapping enforced. |
| Evidence provenance persistence | DONE | 2026-09-19 | `d7b92e5`; immutable artifacts/sources/snapshots/refs, typed reads and fail-loud integrity. |
| Job/JobRequirement persistence | DONE | 2026-09-19 | `3b33525`, `0ee6388`; additive 0008, typed reads and atomic USER-gated review path. |
| Match/Gap pure policy | DONE | 2026-09-19 | `073d3d1`; 15 focused tests, deterministic three-way classification over frozen exact inputs. |
| Match/Gap persistence | DONE | 2026-09-19 | `f3c646e`, `4ff1ac3` merged as `b04d08e`; additive 0009, immutable assessment/result/gap, atomic record service. |
| Match/Gap resolver/replay | DONE | 2026-09-19 | `dd77bd8`, `38616c3` merged as `288ee30`; exact-read resolver, assess orchestration, stored-manifest replay; read-path gap capability check `e82d6cc`. |
| Enhancement task Gap linkage | DONE | 2026-09-19 | `e779c81`, `2abdb2c` merged as `cadba69`; propose/transition commands with fail-loud gap validation. |
| CareerFact domain | DONE | 2026-09-19 | `427ce1b`, `8a76ad2` merged as `d43ebe4`; additive 0010, claim review + revisioned fact promotion. |
| P0 vertical slice proof | DONE | 2026-09-20 | `615bd4d` merged as `f132709`; one fixture walks Job→Opportunity→Match→Fact→Resume→Application→Outcome→replay; full 336 passed. |
| Today read model | DONE | 2026-09-20 | `d36fd00` merged as `1d86b65`; contract `0.8.0`; deterministic projection + authenticated API; full 355 passed. |
| Today UI adapter | DONE | 2026-09-20 | `363e9ea` merged as `c986936`; Today page renders the Core projection; Vitest 22 passed, build passed. |
| Capability inbox review | DONE | 2026-09-20 | `54e2c0d` merged as `3db621d`; contract `0.9.0` + D-019; USER-only acceptance through new graph releases; full 367 passed. |
| Incremental project rescan | DONE | 2026-09-20 | `6b345ff`, `cc8cb43` merged as `693619c`; contract `0.10.0` + D-020; full 371 passed. |
| Interview records | DONE | 2026-09-20 | `834b1fb` merged as `8c44620`; contract `0.11.0` + D-021; additive 0013; full 381 passed. |
| Broad Market Trend | DONE | 2026-09-20 | `f7cb3c6` merged as `c6efb8b`; contract `0.12.0` + D-022; independent review APPROVE with no P0/P1/P2; full 391 passed, 3 skipped; Ruff passed. |
| Capability Workspace Visualization | DONE | 2026-09-20 | Implementation `ae39eb6` + consistency fix `e076daf`, merged as `62f1ce8`; contract `0.13.0`, D-023. Recovery independent review of `f2727cf..e076daf`: APPROVE, no P0/P1/P2/P3. Focused backend 13 passed; full backend 403 passed, 3 known Windows symlink skips; frontend 27 passed; production build, full Ruff, 11 changed Python format checks and diff checks passed. |
| Resume truth core | DONE | 2026-09-20 | `c6bfe66` merged as `df5f4d2`; additive 0011, exact reviewed patches and immutable content-hashed revisions. |
| Today desktop composition | DONE | 2026-09-20 | `7ebd4be` merged as `989b47e`; typed fallback boundary, responsive Today layout, 16 frontend tests/build and visual checks. |
| Application/Outcome contract | DONE | 2026-09-20 | `d61af6c`; contract `0.7.0`, exact submission refs, user authority and no-ATS boundary. |
| Application/Outcome typed invariants | DONE | 2026-09-20 | `5727af6`; exact Opportunity/Application refs, submission authority and receipt evidence gates; 329 passed, 3 skipped. |
| Application/Outcome persistence | DONE | 2026-09-20 | `4b0bb68`; additive 0012, immutable revisions/outcomes, atomic USER-gated services; 332 passed, 3 skipped. |
| Resume/Application/Outcome read API | DONE | 2026-09-20 | `83b7b91`; authenticated read-only exact/latest projections; 334 passed, 3 skipped. |
| Codex to Kimi engineering handoff | DONE | 2026-09-20 | `HANDOFF_CODEX_TO_KIMI_2026-09-20.md`; Git/worktrees, contracts, migrations, UI and verification re-audited. |

## Integrated workstreams

- Opportunity Core: `e09c9a8` merged as `04bccfa`; integration pytest `41 passed, 1 skipped`,
  Ruff passed. Persistence/API follow-up remains Lead-owned.
- Capability Core: `5468c52` merged as `cd5728c`; combined pytest `57 passed, 1 skipped`,
  Ruff passed. Persistence/API and heuristic versioning remain Lead-owned.
- Project Evidence Core: `6df933e` merged as `989fa9e`; combined pytest `72 passed, 1 skipped`,
  Ruff passed. Real scanner resolved-path enforcement remains a follow-up.
- Opportunity Persistence: `3f102f0`; full pytest `75 passed, 1 skipped`, Ruff passed. No legacy
  conversion or production database write occurred.
- Context Core: `c294937` merged as `647f45e`; combined pytest `86 passed, 1 skipped`, Ruff passed.
  Empty relevance selects no context and manifests cannot authorize fact mutation.
- Atomic Opportunity Service: `01e2bbe`; full pytest `92 passed, 1 skipped`, Ruff passed. Hook
  failure rollback, replay and changed typed input conflict are covered.
- Priority/Read/API: `878d222`, `d1004b2`; full pytest `103 passed, 1 skipped`, Ruff passed.
  Manual and Agent-proposal/user-confirmation admissions are available through authenticated API.
- Capability Persistence: `2b7901d`; full pytest `114 passed, 1 skipped`, Ruff passed. Official
  graph releases are immutable and separate from revision-preserving personal overlays.
- Opportunity Desktop: `f888f9a`, `c990589` merged as `f37b92b`, with integration layout fix
  `0cee6c6`; backend `115 passed, 1 skipped`, Ruff passed, frontend `16 passed`, Vite build passed,
  npm audit found 0 vulnerabilities, and desktop/390/320 visual checks passed without overflow.
- Project Evidence Persistence: `158547b`; full pytest `136 passed, 1 skipped`, Ruff passed and
  `0003 -> 0004 -> 0003 -> 0004` rehearsal passed. Canonical capability state and typed basis are
  one deferred-FK transaction; real scanner containment and read repositories remain follow-ups.
- Context Manifest Persistence/Service: `95d3df6`, `6ca47cc`; full pytest `159 passed, 1 skipped`,
  Ruff and format checks passed, and `0004 -> 0005 -> 0004 -> 0005` rehearsal passed. Ordered refs
  and bounded audit metadata are immutable; typed rows, generic revision, event and idempotency are
  atomic; replay returns the first canonical timestamp; compiled content is not stored.
- Capability Read/Identity Guard: `1615581`, `3c2d18c` merged as `7e7dfa5`, Lead fix `61b5a4f`;
  exact/latest official and personal reads preserve identity, Project Evidence bindings pin exact
  revisions, and migration `0006` fails loud on historical identity drift.
- Project Read/Safe Scanner: `116fd50`, `f3cfd9e` merged as `44a3e00`; canonical exact scope is
  loaded by ID, POSIX/Windows scanning is handle-anchored, and unsafe namespaces, drive types,
  reparse points and containment races fail closed. Combined integration: `192 passed, 3 skipped`;
  Ruff passed. Exact Project revision on manifests remains a schema-review follow-up.
- Job Requirement Core: `deadc25` merged as `7728282`; immutable Job revisions and versioned
  requirements keep proposals separate from USER/RULE-reviewed decisions and pin accepted mappings
  to an official graph version. Independent review found no P0/P1; full pytest passed 217 tests.
- Project State Read: `3cb8d5f` merged as `e1182ab`; exact/latest capability state, ordered basis
  and enhancement task reads fail loud on malformed aggregates. Combined integration passed
  `221 passed, 3 skipped`; stable identity trigger coverage was added in `08218e2`.
- Evidence Provenance: `d7b92e5`; additive 0007 stores immutable source snapshots and exact
  artifact-backed EvidenceRefs. Full integration passed `227 passed, 3 skipped`; independent review
  found no P0/P1/P2.
- Job Persistence/Service: `3b33525`, `0ee6388`; additive 0008, typed repositories and atomic
  Job/Requirement commands preserve exact provenance and user-only review. Full integration passed
  `237 passed, 3 skipped`; Ruff, format and diff checks passed; review found no P0/P1.
- Match/Gap Pure Policy: `073d3d1`; full pytest `252 passed, 3 skipped`; Ruff, format and diff
  checks passed. Independent final review found no P0/P1; P2 test gaps (evidence-only coverage,
  rejected/superseded evidence, unreferenced inputs, mismatched personal state and full-input
  reordering equivalence) were added before commit. Durable persistence and the exact input
  resolver are the next slice.
- Match/Gap Persistence: `f3c646e`, `4ff1ac3` merged as `b04d08e`; additive migration 0009 with
  immutable assessment/requirement-result/gap tables, typed reads, an atomic record service and an
  exact Opportunity revision read. Independent review found one P1 (missing Opportunity JobRef
  binding) and P2 validation gaps, all fixed and tested before merge. Full integration passed
  `274 passed, 3 skipped`; Ruff and diff checks passed.

- Match/Gap Resolver/Replay: `dd77bd8`, `38616c3` merged as `288ee30`; the resolver builds
  `MatchPolicyInput` from exact reads only (fail loud on any dangling/missing/identity-drifting
  ref), `assess` orchestrates resolve → pure policy → atomic record, and `replay` re-resolves the
  stored manifest with the stored policy version and fails loud on any drift. Independent review
  found no P0/P1; replay drift-branch tests were added before merge, and the Lead added a
  read-path gap capability check (`e82d6cc`). Full integration passed `292 passed, 3 skipped`;
  Ruff and diff checks passed.
- Resume Core: `c6bfe66` merged as `df5f4d2`; additive 0011 stores immutable Resume Base, Patch
  and Revision aggregates. USER gates, exact Fact/Evidence/accepted Requirement refs, ordered
  accepted patches, fail-loud hash drift, atomic idempotent writes and migration reversal are
  covered. Integration passed `327 passed, 3 skipped`; changed-file Ruff/format and diff checks
  passed (the existing full-file `db/models.py` formatter baseline remains unchanged).
- Today UI: `7ebd4be` merged as `989b47e`; existing router/AppShell now presents the Today
  workspace and eight primary destinations. Data remains a typed fallback adapter until Core owns
  the read model. Frontend passed `16` tests and production build; desktop visual checks passed and
  CDP-forced 390 px layout measured `scrollWidth == innerWidth`.
- Application/Outcome foundation: contract `0.7.0` (`d61af6c`) and typed invariant commit
  `5727af6` keep Application separate from Opportunity, preparation separate from submission and
  Outcome separate from state/signal. Exact refs and receipt evidence are mandatory where
  applicable; no persistence, API or ATS execution was added. Focused tests passed `17`; full
  integration passed `329 passed, 3 skipped`; changed-file Ruff/format and diff checks passed.
- Application/Outcome Persistence: `4b0bb68`; additive 0012 pins exact Opportunity, ResumeRevision,
  Application revision and Evidence refs. Submission identity is DB-stable, Outcome evidence is
  ordered/sealed, receipt source type is checked in service and write layers, and typed rows,
  generic revision, event and idempotency commit atomically. Focused tests passed `11`; full
  integration passed `332 passed, 3 skipped`; changed-file Ruff/format and diff checks passed.
- Career History Read API: `83b7b91`; localhost bearer-authenticated GET projections expose
  ResumeBase, ResumeRevision, latest/exact Application and per-Application Outcome history. No
  Application mutation route or write service is wired into the API. API regression passed `11`;
  full integration passed `334 passed, 3 skipped`; changed-file Ruff/format and diff checks passed.
- Broad Market Trend: `f7cb3c6` merged as `c6efb8b`; the derived read model aggregates only BROAD
  MarketBindings by capability, returns exact binding/evidence refs and the input binding revision
  set, and performs zero canonical writes. Independent review returned APPROVE with no P0/P1/P2;
  full integration passed `391 passed, 3 skipped`, and Ruff passed.

- Capability Workspace Visualization: Implementation `ae39eb6` + consistency fix `e076daf`, merged as `62f1ce8`; contract `0.13.0`, D-023. Recovery independent review of `f2727cf..e076daf`: APPROVE, no P0/P1/P2/P3. Focused backend 13 passed; full backend 403 passed, 3 known Windows symlink skips; frontend 27 passed; production build, full Ruff, 11 changed Python format checks and diff checks passed.
  Real Chromium synthetic populated/no-overlay fixtures passed 320/390/1366 px page-overflow checks.
  Recovery found both integration and feature clean and already merged; no reimplementation or
  duplicate merge was performed. Prior pre-merge review transcript was not present in repository;
  this recovery performed an independent final review rather than inferring an approval.

## Recorded follow-ups (non-blocking)

- `MatchAssessmentWrite.stage()` converges duplicate manifest requirement refs to the last entry
  and raises `KeyError` (not `ValueError`) when a result references an unmanifested requirement;
  both still fail loud and roll back, but error typing is inconsistent (review P3).
- `OpportunityRepository.get_revision()` wraps malformed Opportunity state in `RuntimeError` but
  lets malformed priority rows surface as raw `ValidationError`; harmless for Match replay, which
  never reads priorities (review P3).
- `match_assessment.manifest` has a 64 KB bound; very large inputs fail loud at commit time rather
  than being truncated (capacity calibration note, review P3).
- `get_revision()` relies on the invariant that an Opportunity JobRef never changes after
  admission; any future re-link command must revisit this read (review note).
- `CapabilityRepository` has no point read `get_node(capability_id, graph_version_id)`; the Match
  resolver uses `list_nodes(graph_version_id)` (exact because released graph versions are sealed),
  which is semantically correct but scans the whole version (review P3; add a point read only if a
  real consumer needs it).
- Fresh `assess` callers must enumerate the relevant Project Capability State refs themselves; the
  resolver validates exact refs but does not discover proximity inputs (resolver review note).
- Replay surfaces missing refs as `MatchResolutionError` and stored-output drift as
  `MatchReplayError`; callers must catch both (review P3, unify only if a real caller needs it).
- Claim review accepts a `SUPERSEDED` decision beyond the contract's ACCEPTED/REJECTED pair; it is
  harmless and consistent, but either document the use or narrow it later (review P3).
- `ClaimRecord.reviewed_at` is currently write-only; staged review revisions use the commit
  timestamp instead (review P3).
- Typed fact revision chains have no continuity check on the read path; unreachable via the
  service and guarded by the generic expected-revision check (review P3, defense in depth).
- Today still lacks canonical Interview schedule wiring despite Interview records now existing;
  this is dependency-ready P1 follow-up. A canonical deadline source remains absent (review P2).
- TodayService reads pending reviews via raw read-only SELECTs; promote them to typed repository
  reads when the corresponding review list APIs exist (review P3).
- `MarketTrendService` uses a direct read-only SELECT; add
  `CapabilityRepository.list_broad_market_bindings()` only when another consumer justifies it
  (Broad Market Trend review P3).
- `capability_market_binding` has no DB-level immutable trigger; add revision/immutability semantics
  before introducing any in-place update path (Broad Market Trend review P3).
- `BroadMarketTrend.trend_version` may be narrowed from `str` to
  `Literal["broad-market-trend-v1"]` in a future contract-compatible hardening pass (review P3).
- The zero-write service test compares all table row counts before and after reads; stronger SQL
  write interception is optional defense in depth (Broad Market Trend review P3).

## Latest handoff verification

- Backend full suite at `62f1ce8`: `403 passed, 3 skipped`; skips are Windows symlink privilege limitations.
- Alembic head remains `0013_interview`; Capability Workspace required no migration.
- Ruff lint: passed.
- Ruff format check: baseline failure, 57 files would be reformatted and 97 were already formatted;
  no broad formatting change was made during handoff.
- Frontend: `27 passed`; `tsc -b && vite build` passed.
- Chromium populated/no-overlay synthetic fixtures: 320/390/1366 px, no horizontal page overflow.
  This is browser fixture validation, not a real-data or Tauri end-to-end test.
- Changed Python format check: 11 files passed. Tauri/Rust was not re-run (no shell changes).
