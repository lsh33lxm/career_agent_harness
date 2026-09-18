# Agent Career Harness v1.4 Shared Contracts

**Version:** `v1.4-contract-0.2.0`
**Status:** FROZEN FOR WAVE 1 IMPLEMENTATION  
**Scope:** semantic and cross-module contracts; physical schema remains Lead-owned.

`0.2.0` pins source manifests to scan-scope revisions, pins project capability bases to exact
evidence/approval revisions, scopes approvals to a subject revision and purpose, and requires
explicit user/rule review metadata for non-proposed Project Evidence. Existing Opportunity and
Capability Graph contracts are unchanged.

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

### Priority

`SuggestedPriority` contains level, score/rank if used, reasons, inputs revision set and
`calculated_at`. The system may recompute it.

`UserPriority` contains level, actor, set_at and optional reason. Only a user command may change
it. Recomputing SuggestedPriority must never mutate UserPriority.

Priority levels use `LOW`, `MEDIUM`, `HIGH`, `URGENT`. `URGENT` is valid for suggested urgency;
user interfaces must not infer user intent from it.

## Capability graph

- `CapabilityNode`: stable capability identity, canonical name, description, layer
  (`COMMON_CORE`, `TRACK`, `OPPORTUNITY_SPECIFIC`), lifecycle status and graph version.
- `CapabilityRelation`: directed relation between nodes with a typed relation and graph version.
- `CapabilityGraphVersion`: immutable official graph release with parent version and change note.
- `CandidateCapabilityNode`: AI/rule discovery proposal with source evidence and inbox status;
  it is not part of the official ontology until accepted/merged by policy/user.
- `PersonalCapabilityState`: user-scoped multidimensional state (`understand`, `explain`, `apply`,
  `evidence`, `interview_ready`) plus derived display status. Official upgrades cannot overwrite it.
- `EvidenceBinding`: links capability state to Evidence/Project Evidence with authority and scope.
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
  basis rows are one atomic write; incomplete draft states are not canonical records.
- `ProjectEnhancementTask`: target gap, selected project, learning/files/change/experiment/
  validation plan, expected evidence and status.
- P0 executor is `ManualExecutor`/L1 plan generation. Executor output is a candidate; tests and
  rescan create Evidence, followed by explicit promotion where required.

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
