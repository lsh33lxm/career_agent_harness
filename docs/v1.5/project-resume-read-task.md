# Projects and Resume read clients

Overnight D follow-on: replace two placeholder routes with narrow existing Core
read projections. No new business semantics, no scans or mutations triggered by UI.

Projects: authenticated exact Project read by explicitly entered ID (optional revision),
using existing ProjectRepository; project evidence list via existing method, showing
exact revision/authority/review/freshness and source references. Hide root_locator in
public API DTO, do not open local files. No enumeration or automatic scan needed.
Validate selected project and displayed evidence project identities match; fail loud.

Resume: explicit Resume ID + optional revision lookup via existing GET base endpoint;
optional exact immutable ResumeRevision ID lookup via existing endpoint. Show sections,
candidate ID and exact source refs as returned, distinctly base vs generated revision.
Do not claim rendering/PDF/editing/review is implemented; no auto generation or proposals.

Use shared Guangfu tokens, loading/error/not-found/empty states and long-label wrapping.
Never show "no records" from a placeholder before a successful query. No mock fallback.
Explicit requests, AbortController plus stale-response guards, internal Router Links.

Owned: new project read API module/tests; optional app/runtime wiring; new frontend
project/resume clients/pages/tests and App.tsx. No schema/contracts/store write changes.
Focused backend tests include auth/not-found/exact revision and metadata/root locator
boundary; frontend tests cover input, loading, error/retry and no write requests.
Build/full frontend and 320px visual check. Separate worktree, commit, review then merge.
