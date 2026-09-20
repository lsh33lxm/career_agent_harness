# Scoped L2 Invocation Preparation

Role: implement W2-L2-PREP only. Base 6566d6e. Branch codex/v14-l2-analysis-prep;
worktree sibling agent-career-harness-worktrees/l2-analysis-prep.
Read AGENTS, STATUS, PRD v1.4 sections 20/27/28.5/29, contract 0.15.0 L2 preparation,
D-025, ProjectRepository, ProjectScanScope/Manifest/Task and existing scanner secret exclusions.
User v1.4 authorization overrides historical AGENTS P0F phase restriction.

Owned paths:
- backend/career_harness/core/project/l2.py (new)
- backend/career_harness/adapters/cli_analysis.py (new)
- backend/career_harness/services/l2_preparation_service.py (new)
- tests/unit/test_l2_preparation.py (new)
- tests/integration/test_l2_preparation_service.py (new)

Everything else read-only. No shared contracts, migration, export churn, API, scanner changes,
process execution, credentials, network or actual project content reads. Use existing repository.
Return CONTRACT CHANGE REQUEST if needed. No competing task model.

Implement typed request/file/ref/prepared-envelope and typed unsupported errors, exact read service,
deterministic digest, and Claude fixed argv. Input bytes in memory must match exact manifest and
scope; match hash and byte length, reject duplicates/case collisions, scanner secret/session paths.
Validate all exact identities/revisions/cross-links. Canonical task READY/IN_PROGRESS only.
Preview includes prompt to stdin, selected provider/model/budget/timeout, bound digest and explicit
permission limitations; it grants no consent. No environment or root locator in prompt; no content
in repr/errors. Codex fails unsupported for this no-tool capability. Avoid speculative runner code.
Use bounded input/output types and deterministic sort/canonical JSON; changing refs/content/task/
model/limits changes digest. Simple model identifier only, preserve '--tools', '' in argv.

Tests: unit hostile refs/paths/hashes/lengths/bounds/duplicates/model flags; missing exact data and
cross-project/scope; ready vs terminal tasks; all canonical inputs changing digest; manifest ordering
invariance; actual disposable database exact reads, zero SQL writes; argv/stdin privacy; L1 unaffected.
Run focused new tests plus tests/unit/test_project_enhancement.py, root .venv Ruff/format/diff.
Use fake data only. Explicit stage and focused commit on own branch. No merge/push.
Return SHA, files, exact checks, security impact and remaining boundaries.
