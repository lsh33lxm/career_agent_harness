# Scoped Capability Inbox Client

Base: integration contract freeze commit (parent 3a21d53). Branch codex/v14-capability-inbox-client;
worktree sibling capability-inbox-client. Read AGENTS, STATUS, PRD v1.4 section 12.2,
contract 0.16.0 Inbox client entry and D-026. User authorizes v1.4 beyond historical P0F.

Owned paths:
- backend/career_harness/api/capability_inbox.py (new)
- backend/career_harness/api/app.py (only optional inbox router injection)
- backend/career_harness/api/runtime.py (only inbox runtime composition)
- tests/integration/test_capability_inbox_api.py (new)
- apps/desktop/src/api/capabilityInbox.ts and capabilityInbox.test.ts (new)
- apps/desktop/src/pages/CapabilityInboxPage.tsx and CapabilityInboxPage.test.tsx (new)
- apps/desktop/src/pages/CapabilityInboxPage.css (new, page-scoped)
- apps/desktop/src/pages/CapabilitiesPage.tsx (only inbox navigation link)
- apps/desktop/src/app/App.tsx (only inbox route)

All other paths read-only. No schema, Core/repository/service change, global CSS churn, shared
contract edits or real-data review. If existing Core blocks requirements return CONTRACT CHANGE
REQUEST. Reuse API client and existing request IDs conventions. Do not invent another task model.

Implement list/detail DTO using repository list_candidates and CommandService.get; validate generic
state through CandidateCapabilityNode and equality, exact ID/kind/revision. Missing/inconsistent
audit is sanitized 409, missing candidate 404. Include reviewed history. Stable candidate ID sort.
Review request forbids extra fields and fixes actor user. Use existing service, no pre-PENDING
check that breaks replay. Invalid input 422, conflicts sanitized 409. Nonblank reason. No merge
or bulk/propose route. Runtime must wire the API; injected-only test is insufficient.

Desktop standalone /capabilities/inbox shows pending/history, provenance refs, clear accept-new-
graph vs ignore semantics, explicit reason/submit, receipt and returned canonical IDs. Self-review
user proposals disabled. Loading/empty/error/retry. Retain submitted operation unchanged for lost-
response retry; changed intent gets new ID/key; conflict refresh never auto-resubmits. Mutation
success and read refresh failure are distinct. Keep historical graph queries intact. Safe JSX.

Tests: auth/missing/invalid, true revision not guessed, typed/generic mismatch, actor injection,
self-review, accept/ignore, exact replay no duplicate graph/events, payload/key mismatch, competing
reviews, zero-write GET and actual runtime wiring. Frontend client body/header/path and UI loading/
empty/error, explicit decision, disabled/inflight, conflict, response-loss retry, post-success
refresh failure. Synthetic fixtures only. Run relevant backend tests, full frontend tests/build,
changed Python Ruff/format and git diff --check. Do not format whole repository.

Explicit stage + focused commit, no merge/push. Return SHA, files, commands/results, risks.
