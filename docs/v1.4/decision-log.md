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
