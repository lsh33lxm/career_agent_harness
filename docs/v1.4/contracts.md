# Agent Career Harness v1.4 Shared Contracts

**Version:** `v1.4-contract-0.7.0`
**Status:** FROZEN FOR WAVE 2 APPLICATION/OUTCOME SLICE
**Scope:** semantic and cross-module contracts; physical schema remains Lead-owned.

`0.7.0` retains all `0.6.0` guarantees and adds the Application submission and Outcome contract
below. `0.6.0` added the Resume Base/Patch/Revision write path; `0.5.0` added claim review and Fact
promotion; `0.4.x` added Match persistence/resolver/replay and the enhancement task write path.
Module-specific persisted contract versions remain readable; this document version does not
rewrite historical records.

No workstream may define a competing representation. Missing fields or behavior require a
`CONTRACT CHANGE REQUEST` before implementation.

## Canonical ownership

| Data | Canonical owner | Providers/clients may do |
| --- | --- | --- |
| Personal Context, Career Facts, Career State | Career Core | Propose/query/project |
| Project Evidence and capability state | Career Core | Scan and submit evidence candidates |
| Official Capability Graph | Career Core, versioned | Propose candidate nodes/relations |
| Personal Capability Overlay | Career Core | Propose updates; user/rule confirms by policy |
| Priorities | Core stores both values | System recomputes Suggested; user controls User |
| Resume Base/Patch/Revision | Career Core | Models propose patches; renderers render only |
| Application/Outcome | Career Core | Adapters report receipts/evidence; user confirms |
| Context Manifest/Audit | Career Core | Compiler records exact selected/excluded inputs |

Desktop and Feishu are projections. Adapters, models, scanners, Skills and coding executors never
own truth and never approve their own proposals.
Every approval pins a subject ID and revision plus a typed purpose; an unrelated approval cannot
authorize another domain transition.

## IDs and revisions

- All canonical IDs use the existing `OpaqueId` validation and are Core-generated.
- Prefixes in examples are descriptive, not an approved final ID format. Final opaque ID format
  remains `NEEDS USER APPROVAL` per PRD v1.2.
- Foreign systems' IDs, URLs and paths are locators, never canonical IDs.
- Mutable canonical entities carry `revision >= 1`, `schema_version >= 1`, timestamps and actor.
- Commands require `expected_revision` and `idempotency_key`.
- A commit atomically writes current state, immutable revision, DomainEvent and optional outbox.
- Typed domain rows join that same transaction through a versioned `TransactionalWrite`; its
  business payload participates in the idempotency hash and it is not staged during replay.
- Transactional write failures roll back typed rows, current state, revision, event, outbox and
  idempotency together. Separate best-effort dual writes are forbidden.
- Deletes default to tombstone/supersession; destructive Evidence deletion requires approval.

## Evidence and fact authority

```text
Artifact -> SourceSnapshot -> EvidenceRef -> ExtractedClaim
                                      -> FactProposal
                                      -> explicit review/promotion -> CareerFact
```

- `Evidence` is provenance, not a claim of truth.
- `ExtractedClaim` is parser/model output and cannot become a fact implicitly.
- `FactProposal` packages a proposed fact, evidence refs, proposer, reason and confidence.
- `CareerFact` requires `USER_ASSERTED`, `DOCUMENT_SUPPORTED` or `RULE_VERIFIED` authority.
- Business metrics, personal contribution, ownership and performance claims require user
  confirmation or direct supporting evidence; source code alone is insufficient.
- `Signal`, `Decision` and `Outcome` remain separate typed records.

### Claim review and Fact promotion

- An `ExtractedClaim` is an immutable proposal revision. Review is a separate command
  (`claim.reviewed`) that appends a new claim revision with status `ACCEPTED` or `REJECTED` and a
  reason. Only a USER actor or an explicit deterministic RULE may review; the proposing agent can
  never review its own claim.
- A `Fact` is created only by a promotion command (`fact.promoted`) from an `ACCEPTED` claim, with
  a non-AI `FactAuthority` and exact evidence refs that each resolve through
  `EvidenceRepository.get()`; any dangling ref fails loud. Claims and parser/model output never
  become Facts implicitly.
- Facts are revisioned: corrections append a new revision under the same `fact_id`; prior
  revisions stay immutable and readable.
- Claim review and Fact promotion never mutate Evidence, Capability state, Match results, Gaps or
  Resume material.
- Events `claim.proposed`, `claim.reviewed` and `fact.promoted` carry metadata-only payloads.

## Opportunity and application

```text
Job/Capture -> DiscoverRecord -> WatchlistItem -> Opportunity -> Application
```

- Each stage is a separate record or explicit admission event; it is not a score threshold.
- AI may recommend Watchlist/Opportunity admission. Only a user command or explicit manual add
  creates an Opportunity.
- Opportunity and Application remain separate entities.
- Prepared is not Submitted. Submitted-or-later requires user confirmation or portal receipt.
- Existing `OpportunityState.WATCHING` is compatibility-only until migration to WatchlistItem.

### Application and submission truth

- An `Application` is a revisioned business record distinct from its exact Opportunity revision.
  A USER command creates it when the user chooses to begin serious preparation; recommendation,
  priority or Match score never creates one implicitly.
- `PREPARING` and `READY_FOR_REVIEW` are pre-submission states. They carry no submission authority
  and must never be projected as submitted. Agents may prepare bounded drafts, but only Core may
  append Application revisions.
- A transition to `SUBMITTED_BY_USER` pins the exact `ResumeRevision` used and carries one typed
  `SubmissionAuthority`: `USER_CONFIRMED` from an explicit USER command, or `PORTAL_RECEIPT` backed
  by an exact canonical EvidenceRef whose source is validated as a submission receipt. Missing,
  dangling or mismatched authority fails loud.
- Submitted-or-later states preserve the original submission authority and exact submission
  references. Later adapter observations may propose state changes or receipt evidence; they do
  not overwrite the user's answers or become truth by themselves.
- Identity, legal name, work authorization, demographic disclosures and final form answers remain
  user-controlled. Credentials, cookies, browser profiles and raw portal payloads are never stored
  in Application state, DomainEvents or audit logs. P0 does not execute real ATS submission.
- Application transitions are explicit, expected-revision commands with idempotent replay. A
  transition never mutates the Opportunity, ResumeRevision, Facts, Match assessment or priorities.

### Outcome and career history truth

- An `Outcome` is a separate immutable result record pinned to an exact Application revision. It
  records a typed result, occurrence time, actor/authority and exact supporting EvidenceRefs when
  present; an Application state, Signal or Decision is not itself an Outcome.
- Models and adapters may propose an observed result. USER confirmation or validated deterministic
  receipt evidence is required before it becomes canonical; dangling evidence and agent
  self-confirmation fail loud.
- Recording an Outcome may atomically append the corresponding Application revision, but it never
  rewrites earlier Application history. Recommendation, priority, capability and context changes
  consume Outcome as an input through separate commands; they are not hidden side effects.
- Required events are past-tense and metadata-only: `application.created`,
  `application.state_changed`, `application.submission_recorded` and `outcome.recorded`.

### Priority

`SuggestedPriority` contains level, score/rank if used, reasons, inputs revision set and
`calculated_at`. The system may recompute it.

`UserPriority` contains level, actor, set_at and optional reason. Only a user command may change
it. Recomputing SuggestedPriority must never mutate UserPriority.

Priority levels use `LOW`, `MEDIUM`, `HIGH`, `URGENT`. `URGENT` is valid for suggested urgency;
user interfaces must not infer user intent from it.

## Job and requirement evidence

- `JobRef` always pins `job_id + revision`; latest-at-read is not a frozen Match input.
- `JobRevision` is an immutable, evidence-backed snapshot with stable Job ID, revision,
  `schema_version`, content hash, source Evidence refs and observation time. It does not make
  parser/model claims true by itself.
- `JobRequirement` is revisioned and belongs to one exact `JobRef`. It records requirement text,
  required/preferred importance, official capability ID plus graph version, required evidence
  scopes, source Evidence refs, proposal/review status and actor metadata.
- Parser/model output begins as `ExtractedClaim` or a proposed requirement. Only an accepted
  requirement reviewed by a user or an explicit deterministic rule may enter canonical Match.
- Accepted requirements must map to an Official Capability Graph node at the recorded graph
  version. Unknown concepts remain proposals and may enter `CandidateCapabilityNode`; they do not
  silently expand the ontology.

## Capability graph

- `CapabilityNode`: stable capability identity, canonical name, description, layer
  (`COMMON_CORE`, `TRACK`, `OPPORTUNITY_SPECIFIC`), lifecycle status and graph version.
- `CapabilityRelation`: directed relation between nodes with a typed relation and graph version.
- `CapabilityGraphVersion`: immutable official graph release with parent version and change note.
- `CandidateCapabilityNode`: AI/rule discovery proposal with source evidence and inbox status;
  it is not part of the official ontology until accepted/merged by policy/user.
- `PersonalCapabilityState`: user-scoped multidimensional state (`understand`, `explain`, `apply`,
  `evidence`, `interview_ready`) plus derived display status. One `personal_state_id` keeps the same
  candidate and capability identity across every revision. Official upgrades cannot overwrite it.
- `EvidenceBinding`: links capability state to Evidence/Project Evidence with authority and scope.
  A Project Evidence source always pins both `project_evidence_id` and its exact revision; neither
  field may exist without the other.
- `MarketBinding`: links a capability to a target opportunity/job requirement; target and broad
  market sources are explicitly distinguished.
- `InvestmentState`: explainable factors, recommendation, reasons and calculation inputs. It is a
  proposal, not UserPriority or proof of ability.

Official graph, personal overlay and market bindings use separate tables/repositories even when
joined into one read model.

## Project evidence and enhancement

- `Project`: user-connected project identity and display metadata. A filesystem path is a locator.
- `ProjectScanScope`: explicit allowed paths plus denied paths. Deny wins. No implicit full-disk
  scan, symlink escape or secret/session path access.
- `ProjectEvidence`: evidence-backed observation with a source manifest pinned to the exact
  `ProjectScanScope` revision, scanner/version, authority, freshness and review status.
- `ProjectCapabilityState`: one of `EXISTING`, `UNDERSTOOD`, `MODIFIED`, `EXTENDED`, `VALIDATED`,
  `RESUME_READY`; each basis pins an exact evidence/approval revision, transitions require
  appropriate evidence, and code presence never implies user mastery. A state and all of its typed
  basis rows are one atomic write; `finalized_at` is part of the Core contract and incomplete draft
  states are not canonical records.
- `ProjectEnhancementTask`: target gap, selected project, learning/files/change/experiment/
  validation plan, expected evidence and status.
- Enhancement task creation is a command (`project_enhancement.proposed`); a task starts as
  `PROPOSED`. The write path must validate that the canonical Project exists, that
  `target_gap_id` resolves to a canonical Gap (fail loud on dangling), and that
  `target_capability_id` equals that Gap's capability. Status transitions are separate commands
  (`project_enhancement.status_changed`) that pin the expected revision. Creating or transitioning
  a task never mutates Gaps, Match results, Capability state or Evidence.
- P0 executor is `ManualExecutor`/L1 plan generation. Executor output is a candidate; tests and
  rescan create Evidence, followed by explicit promotion where required.

## Match and capability gap

- `MatchAssessment` is an immutable, explainable proposal based on frozen canonical inputs. It is
  not a Candidate Fact, Personal Capability State, Priority or ontology update.
- P0 classifies every accepted Job Requirement as exactly one of `COVERED`,
  `QUICK_TO_STRENGTHEN`, or `CLEAR_GAP`; it does not require a synthetic overall percentage.
- `COVERED` requires the exact Personal Capability State to satisfy required dimensions and
  qualified non-AI Evidence Bindings to cover those scopes.
- Partial personal progress, missing provenance, or a qualified Project Capability State may yield
  `QUICK_TO_STRENGTHEN`. Project presence alone can never yield `COVERED` or personal mastery.
- `CLEAR_GAP` means only that the frozen Core input set has no qualified coverage or proximity; it
  must not claim the user objectively lacks the capability outside recorded evidence.
- Inputs pin Opportunity, Job, Requirement, Official Graph, Personal Capability State,
  Evidence/Project Evidence and Project Capability State identities/revisions plus policy version.
  Ambiguous personal-state identities or missing/stale revisions fail closed.
- Output reasons use typed reason codes and reference only frozen inputs. The same ordered inputs
  and policy version must produce the same business output.
- Match/Gap never writes Career Facts, Personal Capability State, SuggestedPriority, UserPriority,
  Official Capability Graph or accepted Resume material.

### Match persistence

- A persisted `MatchAssessment` has a Core-generated `assessment_id`, is immutable and carries a
  single revision. Re-assessment creates a new assessment; supersession is expressed by a newer
  assessment, never by mutation.
- The exact `MatchInputManifest` (policy version plus every frozen input ref) is persisted with the
  assessment as a bounded immutable canonical JSON snapshot. It is the only replay source.
- Each requirement result is a typed row keyed by `(assessment_id, requirement_id,
  requirement_revision)` with classification, covered/missing scopes and a bounded reasons payload.
  Reason details are immutable payload, not queryable identity.
- Every `QUICK_TO_STRENGTHEN` or `CLEAR_GAP` result receives a stable Core-generated `gap_id` in the
  same transaction. A `Gap` row pins `assessment_id`, exact `(requirement_id, requirement_revision)`
  and `capability_id`; it is immutable, and a newer assessment mints new gaps instead of mutating
  old ones.
- `ProjectEnhancementTask.target_gap_id` must resolve to a canonical Gap at task write time. The
  column predates the Gap table, so no retroactive FK is added to the existing task table; the
  enhancement-task write path must validate resolvability (fail loud on dangling) once that write
  path exists.
- Assessment, typed results, gaps, generic revision, the `match.assessed` event and the idempotency
  record commit in one transaction through a versioned `TransactionalWrite`. The event payload is
  metadata only: ids, exact revisions, policy version and per-classification counts.
- Match persistence never mutates Career Facts, Personal Capability State, priorities, ontology or
  Resume material.

### Match resolver and replay

- A resolver builds `MatchPolicyInput` from exact reads only: Opportunity by
  `(opportunity_id, revision)`; Job by `JobRef`; Requirements by the caller-supplied ordered
  `(requirement_id, revision)` refs; official nodes by `(capability_id, graph_version_id)`; Personal
  Capability States by `(personal_state_id, revision)`; Evidence Bindings by exact personal state
  revision; every generic EvidenceRef through `EvidenceRepository.get()`; Project Evidence by
  `(evidence_id, revision)`; Project Capability States by `(capability_state_id, revision)`.
- Any missing, stale-identity or dangling reference fails loud. The resolver never skips,
  substitutes or downgrades provenance.
- `OpportunityRepository.get()` reads the current projection only. Match persistence requires an
  exact-revision Opportunity read; current-projection reads are not a frozen Match input.
- Replay loads the stored manifest, re-resolves every ref by exact read, re-runs the stored
  `policy_version` and compares the full business output. Drift, missing refs or an unknown policy
  version fail loud. Replay never writes and never uses latest-at-read APIs, including
  `JobRepository.list_requirements_for_job()` and `OpportunityRepository.get()`.

## Context compiler and manifest

The compiler selects from five asset classes: Personal Context, Career State, Project Evidence,
Market Evidence and Career History/Outcomes. It must not default to sending all stored context.

`ContextManifest` records task type, included refs with revisions, excluded refs with reasons,
compression/selection policy version, vertical knowledge refs, model/provider, capabilities/skills,
input hash, created_at and actor/run. Manifest creation does not authorize fact mutation. P0
persistence stores this audit metadata only; it does not persist task input, asset/knowledge payloads,
assembled context or compiled prompt content by default. Capability and skill audit names are
bounded to 64 entries per list and 128 characters per entry so they cannot become content channels.
Matched relevance terms use the same 64-entry and 128-character bounds.

## Resume truth

```text
ResumeBase revision + reviewed ResumePatch -> immutable ResumeRevision -> ResumeRender
```

Every patch operation records expected value hash, fact/evidence refs, job requirement refs, reason,
generator run and review status. AI-inferred material is ineligible for an accepted formal patch
until promoted to a qualified CareerFact.

### Resume write path

- A `ResumeBase` belongs to one candidate and holds revisioned structured content (bounded JSON
  sections). Only USER commands create or revise a base resume; imports and agent drafts are
  proposals the user must save explicitly.
- A `ResumePatch` targets an exact `(resume_id, base_revision)`. Each operation carries
  `operation`, `target_path`, `expected_value_hash`, `proposed_value`, exact `(fact_id, revision)`
  refs, exact EvidenceRef ids, exact `(requirement_id, revision)` refs, a reason and an optional
  generator run id. Patch proposals are immutable revisions; review (`resume_patch.reviewed`) is a
  USER-only command appending a review revision (`ACCEPTED`/`REJECTED`). The proposing agent can
  never review its own patch.
- The write path resolves every fact ref to a canonical Fact with non-AI authority and every
  evidence ref through `EvidenceRepository.get()`; dangling or unqualified refs fail loud.
- A `ResumeRevision` is an immutable, content-hashed snapshot derived from one exact base revision
  plus an ordered list of accepted patch revisions. Creation (`resume_revision.created`) is a
  USER-gated command that re-verifies every referenced patch is accepted against the same base
  revision. Rendering (`ResumeRender`) is a projection and never feeds back into truth.
- Resume writes never mutate Facts, Evidence, Capability state, Match results or priorities.

## Domain events

The shared envelope remains `event_id`, `event_type`, entity ref/revision, command ID, payload and
occurred_at. Event types are explicit inputs to repository commits, use past-tense domain language
(for example `opportunity.admitted`) and are included in the idempotency request hash.

Domain event payloads may add reviewed domain references but cannot override the Core-generated
`revision_id`. Audit-only timestamps are excluded from business idempotency payloads; IDs,
revisions, decisions and other typed domain inputs are included.

Minimum P0 events include proposal created/reviewed, opportunity admitted, priority suggested/user
set, project scanned/evidence proposed, capability binding/state changed, context compiled, resume
patch proposed/reviewed, application prepared/submitted and outcome recorded.

## Persistence ownership

- Lead/integration owns global migrations, ORM registration and shared event/ID definitions.
- Domain workstreams own domain models, services, repositories and tests within assigned paths.
- Wave 1 domain storage is relational SQLite. JSON is allowed for bounded immutable payloads, not
  as a substitute for identity, lifecycle or queryable relationships.
- Existing generic entity tables remain for compatibility until migrated; no destructive rewrite.
