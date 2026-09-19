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
| Resume truth core | DONE | 2026-09-20 | `c6bfe66` merged as `df5f4d2`; additive 0011, exact reviewed patches and immutable content-hashed revisions. |
| Today desktop composition | DONE | 2026-09-20 | `7ebd4be` merged as `989b47e`; typed fallback boundary, responsive Today layout, 16 frontend tests/build and visual checks. |

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

## Baseline verification

- Python: `31 passed, 1 skipped` before Wave 0 edits.
- Ruff: passed before Wave 0 edits.
- Frontend/Rust: last full verified results are in `GOAL_COMPLETION_REPORT.md`; rerun at Wave 0
  close because shared backend-only changes do not touch those surfaces.
