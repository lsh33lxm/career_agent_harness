# Scoped L1 offline acceptance

Base bb05e99; branch codex/v14-l1-offline-acceptance, sibling worktree l1-offline-acceptance.
No new contract semantics: shared 0.16.0, existing L1 contract and PRD section 29 item 7.
Read STATUS, current PRD, core/project/executor.py, ProjectService and existing enhancement tests.
Owned path ONLY tests/integration/test_l1_offline_acceptance.py (new). All production code/docs
read-only. No host environment change, real integrations, project writes or CLI/provider calls.

Create a meaningful disposable DB acceptance fixture using existing canonical Project/Gap helpers.
Use real L1ManualExecutor -> complete PROPOSED ProjectEnhancementTask -> real ProjectService
propose, exact read, idempotent retry, supported READY/IN_PROGRESS/etc state flow. Task completion
is not real code execution/evidence/mastery. Compare protected tables/state before/after and a
synthetic target source tree to prove no change. Block CLI discovery (shutil.which), subprocess
and network calls throughout tested generation/service path; no provider configuration. Avoid
brittle global patches that prevent pytest/SQLAlchemy setup. Do not fake the service/executor.
Do not claim actual Browser/LLM/Skill replacement. No product changes required; request scope
change if a real product bug blocks. Run new test plus L1 unit and project enhancement integration,
Ruff/format/diff, explicit stage and focused commit. No merge/push. Return SHA/results/limits.
