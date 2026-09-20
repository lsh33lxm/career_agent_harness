# v1.4 Architecture Decision Log

## D-001 - Use existing kernel and additive vertical slices

**Decision:** PROPOSED implementation direction.

**Context:** The repository already has authenticated local API, SQLite revision/event substrate,
ArtifactStore, backup/restore, evidence boundaries and a desktop shell.

**Alternatives:** Big-bang rewrite; extend every feature through generic JSON state.

**Chosen:** Retain the kernel, add typed relational domain slices incrementally, and keep generic
state as a compatibility substrate.

**Reason:** Preserves verified invariants and enables narrow rollback without cementing unqueryable
domain state.

**Impact:** New domain schema remains Lead-owned; workstreams use shared contracts.

## D-002 - Separate engineering subagents from product multi-agent runtime

**Decision:** ACCEPTED for development organization.

**Context:** The v1.4 master prompt requests scoped parallel engineering; PRDs forbid a premature
multi-agent product platform.

**Alternatives:** Serial development only; implement a runtime multi-agent framework.

**Chosen:** Use independent Git worktrees and scoped coding subagents only. Do not add multi-agent
runtime code.

**Reason:** Gains parallel delivery without expanding product scope.

**Impact:** Every subagent has owned paths, forbidden shared files and a merge review gate.

## D-003 - Keep Watchlist distinct from Opportunity

**Decision:** PROPOSED pending implementation review.

**Context:** v1.4 defines an explicit funnel; current code models `WATCHING` inside Opportunity.

**Alternatives:** Continue treating watch as Opportunity state; introduce `WatchlistItem`.

**Chosen:** Introduce a separate Watchlist record and preserve `WATCHING` only through a temporary
compatibility mapping.

**Reason:** Enforces user-gated investment and avoids inflating formal Opportunities.

**Impact:** Requires additive migration and compatibility tests; no automatic real-data conversion.

## D-004 - Explicit event type is part of idempotency

**Decision:** ACCEPTED in Wave 0.

**Context:** `RevisionRepository` required event type while `CommandService` generated one and
returned an incompatible type.

**Alternatives:** Remove event type from the protocol; keep stringly generated events.

**Chosen:** Callers provide the domain event type; it participates in request hashing; commits
return a typed result.

**Reason:** Prevents one idempotency key from replaying a semantically different event.

**Impact:** Existing internal call sites are updated; there is no public domain API yet.

## D-005 - Physically separate Opportunity authority records

**Decision:** ACCEPTED in Wave 1 migration 0002.

**Context:** AI proposals, user admission decisions, canonical Opportunities, system priority and
user priority have different owners and mutation rules.

**Alternatives:** Store all fields in one Opportunity JSON/table; use one mutable priority column.

**Chosen:** Use distinct relational tables for Watchlist, admission proposal, admission decision,
canonical Opportunity, SuggestedPriority and UserPriority. Enforce user-only decision/priority at
both Pydantic and SQLite constraint boundaries.

**Reason:** Prevents recomputation or adapter writes from silently becoming user intent.

**Impact:** More explicit joins, but authority and audit semantics stay inspectable and testable.

## D-006 - Typed domain writes participate in the command transaction

**Decision:** ACCEPTED in `01e2bbe`.

**Context:** `CommandService` previously owned its Session, so typed Opportunity rows could only be
written before or after revision/event records in a separate transaction.

**Alternatives:** Best-effort dual write; move transaction ownership into every domain service;
provide a versioned transaction participant.

**Chosen:** `CommandService` accepts a `TransactionalWrite` that exposes a versioned idempotency
payload and stages typed rows after revision validation within the same Session.

**Reason:** Preserves the existing atomic revision/event/idempotency kernel without teaching it
Opportunity semantics or allowing partial canonical truth.

**Impact:** Domain DB mappers remain infrastructure adapters. Hook failure rolls back all records;
replay returns the original receipt without staging the hook again.

## D-007 - Version official capability data around a stable identity

**Decision:** ACCEPTED in migration `0003_capability_core`.

**Context:** Official nodes retain a stable capability ID across immutable graph releases, while
personal state and bindings must survive ontology upgrades without being overwritten.

**Alternatives:** Make capability ID unique per release; overwrite one mutable node row; store the
graph and overlay together as JSON.

**Chosen:** Store stable IDs in `capability_identity`, version official nodes by the composite
`(capability_id, graph_version_id)`, and keep revisioned personal state in a separate table. Build a
release in one deferred-FK transaction and insert its graph version last; SQLite triggers then seal
the version, nodes and relations against append/update/delete.

**Reason:** Preserves stable cross-domain references and immutable ontology history without letting
official graph upgrades mutate the user's capability overlay.

**Impact:** Graph publishing requires one transaction with the release row staged last. Capability
repository work must preserve this order and use additive graph versions for every change.

## D-008 - Persist Project Capability provenance as an atomic relational aggregate

**Decision:** ACCEPTED in migration `0004_project_evidence`.

**Context:** `ProjectCapabilityState` must distinguish code presence from user mastery and must pin
the exact Evidence and user Approval revisions that authorize stronger states such as
`RESUME_READY`. A JSON basis cannot enforce reference authority, revision identity or project scope.

**Alternatives:** Keep basis as JSON; persist an independently committed nullable draft state;
introduce a separate staging table.

**Chosen:** Store typed basis edges in `project_capability_basis`. Insert basis rows first and the
non-null canonical state last in one transaction using a deferred composite FK. SQLite triggers
validate accepted Evidence authority, same-project scope, required basis kinds and a user-approved
subject/revision/purpose before the aggregate commits, then seal both state and basis as immutable.

**Reason:** The database can reject orphan, cross-project, unrelated-approval and partially formed
canonical states without introducing a workflow engine or storing queryable provenance as JSON.

**Impact:** Repository writes must stage all basis rows and the final state in one transaction.
Migrations never scan project files; resolved-path and reparse-point containment remains scanner
responsibility.

## D-009 - Persist Context Manifest metadata without compiled content

**Decision:** ACCEPTED in migration `0005_context_manifest`.

**Context:** Important model calls need auditable input selection and model/tool provenance, but
persisting task input, asset payloads, injected knowledge or assembled prompts would duplicate
sensitive long-term context and enlarge the local disclosure surface.

**Alternatives:** Store the full compiled request/prompt; store all refs and metadata in one JSON
blob; store no invocation provenance.

**Chosen:** Persist an immutable parent-last aggregate containing policy/model/run metadata plus
ordered relational asset and knowledge references. Capabilities, skills and matched terms are
bounded to 64 entries and 128 characters per entry. Store only the deterministic input hash, never
the compiled content or a fact-mutation authority flag.

**Reason:** Exact revisions and exclusions remain queryable for Preview AI Context and audit while
sensitive source content stays in its canonical domain stores and transient compiler output.

**Impact:** A future write service must stage children then seal the parent in the same command
transaction and emit metadata-only `context.compiled`. Retention remains append-only until the user
approves a retention policy.

## D-010 - Keep Personal Capability identity stable across revisions

**Decision:** ACCEPTED in migration `0006_capability_personal_state_identity`.

**Context:** Revision-exact reads are ambiguous if one `personal_state_id` can silently change its
candidate or capability identity in a later revision.

**Alternatives:** Infer identity from the latest row; split every changed identity at read time;
introduce a new identity table immediately.

**Chosen:** Preserve the existing relational representation and add insert/update guards. Upgrade
fails without rewriting data when historical drift already exists. Project Evidence bindings carry
their exact evidence revision in the shared domain contract.

**Reason:** This closes identity drift with a small additive migration while preserving every
canonical record and keeping official ontology, personal overlay and evidence provenance separate.

**Impact:** Any discovered historical drift requires explicit reconciliation before upgrade. Read
repositories return the canonical `EvidenceBinding` without an infrastructure-only envelope.

## D-011 - Scan Project Evidence through canonical, handle-anchored inputs

**Decision:** ACCEPTED in `f3cfd9e` and merge `44a3e00`.

**Context:** Caller-provided scope objects can widen authorization, and path checks followed by a
separate open leave a symlink/junction replacement window.

**Alternatives:** Trust validated Pydantic scope objects; resolve paths before ordinary open;
disable local scanning.

**Chosen:** Load Project and exact scope revision from Career Core by canonical IDs. On POSIX,
traverse from directory descriptors with `O_NOFOLLOW`; on Windows, require a fixed local drive,
hold no-delete/no-write-shared handles, reject reparse points, verify final-path containment and
read from the verified file handle. Reject UNC and device namespaces before filesystem access.

**Reason:** Authorization and bytes read now derive from the same canonical scope and anchored
filesystem objects, closing both forged-scope and check/open races without a new dependency.

**Impact:** Unsupported platforms and non-fixed Windows drives fail closed. Exact Project revision
on `ProjectSourceManifest` remains a future shared-schema review, not an implicit scanner claim.

## D-012 - Keep JobRequirement identity stable at the Job boundary

**Decision:** ACCEPTED in migration `0008_job_requirement_persistence`.

**Context:** A Requirement must remain part of one Job, while later reviewed revisions may correct
which immutable Job revision or official capability mapping supports it.

**Alternatives:** Bind the identity permanently to its first exact Job revision; allow a Requirement
identity to move between Jobs; keep only a mutable latest Job reference.

**Chosen:** Store stable `(requirement_id, job_id)` identity. Every Requirement revision separately
pins an existing exact `JobRef`, source EvidenceRefs and, when accepted, an exact official
CapabilityNode plus graph version. A Requirement identity cannot move to another Job.

**Reason:** Job identity is the durable semantic boundary. Freezing the first Job revision would
prevent audited corrections, while allowing cross-Job movement would corrupt identity history.

**Impact:** Services must append a new Requirement revision for corrections and retain all prior
exact references. Match/Gap consumers must freeze the exact Requirement and Job revisions they use.

## D-013 - Treat any canonical Project Capability State as qualified proximity input

**Decision:** ACCEPTED in `073d3d1`.

**Context:** The Match contract says a "qualified Project Capability State" may yield
`QUICK_TO_STRENGTHEN`, but the pure policy receives typed domain objects rather than raw rows, and
the `ProjectCapabilityState` model already enforces a state-appropriate basis at construction.

**Alternatives:** Re-validate basis sources inside the policy; require a minimum capability level
before proximity counts; treat only `VALIDATED` or `RESUME_READY` states as proximity.

**Chosen:** Any canonical `ProjectCapabilityState` instance is qualified by construction and may
contribute proximity (`QUICK_TO_STRENGTHEN`) only. The policy never promotes project presence to
personal coverage, and exact `(capability_state_id, revision)` plus ordered basis refs are recorded
in the frozen input manifest for later replay.

**Reason:** Basis legitimacy is enforced where the aggregate is written; duplicating that check in a
pure policy would couple it to write-path rules without adding safety. Proximity stays cheap and
explainable at this stage.

**Impact:** Resolver/persistence work must load exact Project Capability State revisions and fail
loud on dangling provenance. A future minimum-level threshold is a policy-version change, not a
silent filter.

## D-014 - Persist Match as immutable assessment plus canonical Gap rows

**Decision:** ACCEPTED in contract `0.4.0` (docs-only freeze; schema lands in migration 0009).

**Context:** The pure Match/Gap policy is deterministic over frozen inputs, but
`ProjectEnhancementTask.target_gap_id` needs a resolvable canonical Gap, and historical Match must
be replayable without re-deriving inputs from latest-at-read APIs.

**Alternatives:** Store only the assessment payload as JSON; recompute gaps on read; let
`list_requirements_for_job()` or the Opportunity current projection stand in for historical inputs;
add a retroactive FK from `target_gap_id` to a new Gap table.

**Chosen:** Persist each assessment as an immutable single-revision record with its exact
`MatchInputManifest` as a bounded canonical JSON snapshot, typed requirement-result rows for
queryability, and stable `gap_id` rows minted in the same transaction for every non-COVERED result.
Replay re-resolves the manifest through exact reads and fails loud on any drift. `target_gap_id` is
validated at the task write path because the column predates the Gap table.

**Reason:** The manifest snapshot is the only faithful replay source; typed result/gap rows keep Gap
linkage and per-requirement queries relational; write-path validation closes the dangling-reference
hole without rebuilding the existing task table.

**Impact:** Migration 0009 must be additive with immutable triggers on assessment, result and gap
tables. Resolver work adds an exact-revision Opportunity read and must resolve every generic
EvidenceRef through `EvidenceRepository.get()`. Reassessment always mints a new assessment and new
gaps.

## D-015 - Promote accepted Claims to revisioned Facts through explicit commands

**Decision:** ACCEPTED in contract `0.5.0` (docs-only freeze; schema lands in migration 0010).

**Context:** The Resume patch contract requires resolvable qualified fact refs, but `Fact` and
`ExtractedClaim` existed only as in-code skeletons with no persistence, and the core stub
`promote_claim_to_fact` deliberately raises. Without canonical Facts, no downstream Resume or
Capability promotion can reference verified personal claims.

**Alternatives:** Let Resume patches reference EvidenceRefs directly without a Fact layer; store
claims and facts as JSON payloads on the generic entity tables; allow rule promotion without user
review for all claim types.

**Chosen:** Persist claims as immutable proposal revisions reviewed by a separate USER or explicit
RULE command, and promote accepted claims into revisioned Facts whose every evidence ref resolves
through `EvidenceRepository.get()`. The proposing agent can never review or promote its own claim.

**Reason:** This preserves Evidence != Fact, keeps AI output from self-promoting, and gives Resume
and Capability consumers a resolvable, auditable canonical Fact identity without coupling them to
parser internals.

**Impact:** Migration 0010 must be additive with claim/fact tables, review guards and immutable
history. Downstream workstreams (Resume patch, capability promotion) consume exact
`(fact_id, revision)` refs.

## D-016 - Resume truth as base revisions plus reviewed patches

**Decision:** ACCEPTED in contract `0.6.0` (docs-only freeze; schema lands in migration 0011).

**Context:** The vertical loop needs JD-specific resume material without maintaining drifting
independent resume copies, and every claim on a resume must trace to qualified Facts or Evidence.

**Alternatives:** Store one mutable resume document per opportunity; let patch review be an
agent-approvable transition; store rendered resume content as canonical state.

**Chosen:** A candidate-owned `ResumeBase` holds revisioned structured content. A `ResumePatch`
pins an exact base revision and carries per-operation expected value hashes plus exact fact,
evidence and requirement refs; only USER review can accept a patch. An immutable, content-hashed
`ResumeRevision` derives from one base revision plus ordered accepted patch revisions. Rendering is
a projection only.

**Reason:** This keeps a single canonical base, makes every AI-proposed change auditable and
user-gated, and lets any historical resume be reconstructed from immutable parts.

**Impact:** Migration 0011 must be additive. The write path resolves fact refs to non-AI Facts and
evidence refs through `EvidenceRepository.get()`, failing loud on dangling provenance. Renderer and
desktop diff UI are later projections over these records.

## D-017 - Application submission and Outcome are separate user-authorized truth

**Decision:** ACCEPTED in contract `0.7.0` and implemented by additive migration
`0012_application_outcome` plus Application/Outcome services and read projections.

**Context:** ResumeRevision now provides an immutable artifact for a real opportunity, but the
existing lifecycle skeleton alone cannot prove which opportunity/resume was submitted, distinguish
preparation from submission, or preserve employer results as auditable Career History.

**Alternatives:** Treat Opportunity state as the application funnel; let an adapter mark submission
from its own success response; store raw ATS form payloads and credentials for replay; infer Outcome
from the latest Application state.

**Chosen:** Create revisioned Applications from exact Opportunity revisions only by USER intent.
Submission pins the exact ResumeRevision and requires explicit USER confirmation or an exact
validated portal-receipt EvidenceRef. Store Outcomes separately as immutable, authority-qualified
results pinned to exact Application revisions. Keep sensitive form answers user-controlled and out
of generic state/events; P0 performs no real ATS submission.

**Reason:** This enforces Opportunity != Application, Prepared != Submitted and Outcome != Signal,
keeps adapters from owning truth, and preserves reconstructable history without retaining browser
credentials or uncontrolled legal/identity answers.

**Impact:** Typed Application/Outcome models, additive persistence and atomic services now resolve
exact Opportunity/Resume/Evidence refs, preserve submission authority across later revisions and
avoid hidden mutations of Resume, Facts, Match, Capability or priorities. Real ATS submission and
sensitive form/credential persistence remain forbidden.

## D-018 - Today as a deterministic Core projection, never a persisted queue

**Decision:** ACCEPTED in contract `0.8.0` (docs-only freeze; no schema change).

**Context:** The desktop Today page currently renders static typed fallback data, which can drift
from canonical truth and create false confidence. A persisted queue table would duplicate business
state and invite staleness; client-side ranking would move business truth into React.

**Alternatives:** Persist a Today queue table refreshed by commands; compute ranking in the desktop
client; reuse SuggestedPriority alone as the queue.

**Chosen:** Today is a pure read model computed by Core from exact source revisions. Item kinds are
a closed typed set; ordering is a documented total order (user priority, suggested priority,
earliest deadline/interview, stable item ID); missing inputs rank explicitly low with reason codes;
the response carries the input revision set for staleness detection.

**Reason:** A deterministic projection is replayable and testable without new truth tables, keeps
priority separation intact and lets the frontend stay a pure renderer.

**Impact:** The Today service/API and the frontend adapter must consume this contract; replacing the
static fallback happens only after the Core read model is implemented and reviewed. No migration is
required.

## D-019 - Capability inbox review promotes only through a new graph release

**Decision:** ACCEPTED in contract `0.9.0` (docs-only freeze; implementation in a later workstream).

**Context:** AI/rule discovery proposes `CandidateCapabilityNode` records, but released official
graph versions are immutable (D-007). A review decision therefore cannot simply flip a flag on a
released node.

**Alternatives:** Mutate the released graph in place on acceptance; auto-accept high-confidence
candidates; keep accepted candidates forever outside the official ontology.

**Chosen:** Acceptance is USER-only and enters the ontology only via a new graph version release
with the current release as parent, or via an explicit merge into an existing identity. Rejection
may be USER or RULE. Reviewed candidates remain immutable history.

**Reason:** Preserves immutable official history, keeps AI discovery from self-expanding the
ontology and keeps every acceptance auditable.

**Impact:** The review service must assemble the new graph version in one transaction (D-007
ordering) and must never touch personal overlays, bindings, Match results or priorities.

## D-020 - Incremental rescan records diffs; staleness changes are explicit commands

**Decision:** ACCEPTED in contract `0.10.0` (docs-only freeze; implementation in a later workstream).

**Context:** The scanner currently performs full scans per scope. Rescans after enhancement work
must refresh Project Evidence freshness without silently rewriting accepted evidence.

**Alternatives:** Auto-mark evidence stale inside the scan; full-rescan only (no diff); rewrite
evidence rows in place.

**Chosen:** A rescan produces a new manifest revision plus an auditable added/changed/removed diff
record. Freshness transitions (`CURRENT` -> `STALE`) happen only through an explicit command with
a typed event; accepted evidence content is never mutated.

**Reason:** Keeps evidence immutable and auditable while letting the enhancement loop detect when
previously accepted evidence no longer matches the project.

**Impact:** The rescan service reuses the existing anchored readers and scope validation unchanged.
Any freshness-change command must list affected evidence ids and the manifest revision that
motivated the change.

## D-021 - Interviews are revisioned records that never create Outcomes

**Decision:** ACCEPTED in contract `0.11.0` (docs-only freeze; implementation in a later
workstream).

**Context:** The Interview entity was a bare skeleton, yet the vertical loop needs scheduled
interviews to feed Today ordering and interview outcomes must not silently become Outcomes.

**Alternatives:** Fold interview state into the Application state machine; let an interview result
auto-record an Outcome; keep interviews as free-form notes.

**Chosen:** An Interview is its own revisioned record pinned to an exact Application revision with
a typed round and explicit schedule/complete/cancel commands. Outcomes stay on their own
user/receipt-gated path.

**Reason:** Keeps workflow state separate from business results and keeps every transition
auditable.

**Impact:** A later workstream adds additive persistence for interviews; Today ordering can then
consume scheduled times as a real input.

## D-022 - Broad Market Trend is a derived read model, never an authority

**Decision:** ACCEPTED in contract `0.12.0` (docs-only freeze; implementation in a later
workstream).

**Context:** Market Evidence separates Target from Broad. Investment planning must not let generic
market noise outweigh target-scope evidence, and AI-discovered trends must not silently reshape the
capability ontology or priorities.

**Alternatives:** Persist computed trend tables; let trend frequency directly rank investment;
merge broad and target signals into one score.

**Chosen:** Broad Market Trend is computed on read from broad-scope MarketBinding records with the
input revision set recorded. It never writes, never reweights target inputs and never mutates
priorities, overlays or the ontology.

**Reason:** Keeps market signals explainable and replayable while preventing broad trends from
deciding what the user should become.

**Impact:** A later workstream adds a trend read service and optional API projection; no migration
is needed.

## D-023 - Compose Capability Visualization as a candidate-scoped read model

**Decision:** ACCEPTED in contract `0.13.0` (docs-only freeze; no schema change).

**Context:** Official graph, personal overlay, evidence/market bindings, InvestmentState and Broad
Market Trend exist, but the desktop Capability route is a placeholder. Rendering these stores
independently in React would move join semantics into the client and risk mixing candidate identity,
target demand, broad trends and proposals.

**Alternatives:** Let the client call each repository-shaped endpoint and join locally; persist a
denormalized capability dashboard; render only the official graph without personal/market context.

**Chosen:** Core produces one deterministic, candidate-scoped Capability Workspace projection over
one selected official graph version. It keeps official, personal, evidence, target, broad and
investment fields distinct, records the exact input set and never writes. The client owns layout
and selection only.

**Reason:** This makes the existing capability assets inspectable without creating a second truth,
leaking another candidate's overlay or allowing broad-market frequency to masquerade as a personal
investment decision.

**Impact:** The implementation adds repository list reads where needed, a pure assembly service,
an authenticated read endpoint and a responsive desktop visualization. No migration or canonical
write path is permitted. Missing identity context remains explicit rather than guessed.
