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

