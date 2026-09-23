# PRD v1.4 section 29 acceptance evidence

Baseline: integration `6ba054d`, full 551 passed, 3 skipped; frontend 39 passed/build.
This matrix distinguishes absent dependencies from implemented adapter replacement. It does not
claim the entire PRD is complete. Synthetic fixtures never authorize real integration operations.

| Item | Evidence | Current verdict / limit |
| --- | --- | --- |
| 1. Core works without Feishu | P0 vertical slice and local runtime run without a Feishu adapter or config | Absence-of-dependency proven; no installed adapter toggle/uninstall exists |
| 2. Core works without GitHub | Local Project/Gap/task and Evidence persistence use disposable SQLite | Absence-of-dependency proven; no installed adapter toggle/uninstall exists |
| 3. Replace Browser Worker | Typed Job/Evidence contracts and canonical persistence exist | NOT IMPLEMENTED: no Browser Worker port and interchangeable implementations |
| 4. Replace LLM without losing canonical data | Provider/model are Context audit metadata; canonical Facts/Outcomes persist independently | PARTIAL architecture evidence only; no implemented LLM invocation swap, full Personal Context not demonstrated |
| 5. Install Skill without Kernel edits | Context accepts skill-name metadata | NOT IMPLEMENTED: name metadata is not a Skill loader/install lifecycle |
| 6. Remove Skill without losing canonical data | Skill names do not own canonical rows | NOT IMPLEMENTED: no real uninstall lifecycle tested |
| 7. L1 without Claude/Codex | Real ManualExecutor/L1ManualExecutor and ProjectService already exist | PASS: `aa08afa`, merge `3626994`; real L1 generation/persistence/replay/status with forbidden CLI/process/network entry points |
| 8. Replace Coding Executor, same task contract | ManualExecutor Protocol returns existing ProjectEnhancementTask; L2 preparation adds no competing task | PARTIAL: one real L1 implementation, no interchangeable live Coding Executor runtime; Codex L2 explicitly unsupported |

## Existing checks

Independent preflight ran `tests/unit/test_project_enhancement.py`,
`tests/integration/test_project_enhancement_service.py`, and
`tests/integration/test_p0_vertical_slice.py`: 13 passed. These establish existing behavior, not
actual Browser/LLM/Skill replacement. Inbox and L2 preparation changes do not alter this distinction.

## Item 7 accepted proof

Implementation `aa08afa`, merge `3626994`; independent review APPROVE, P0-P3 none.
Worker and reviewer each ran the new acceptance, L1 unit and Project Enhancement service tests:
12 passed. Full integration at `3626994`: 552 passed, 3 skipped; full Ruff, changed-file
format and diff checks passed. No production code changed after the verified Inbox build.

The test uses real L1ManualExecutor and ProjectService with canonical synthetic Project/Gap data.
It verifies complete PROPOSED plans, exact revision reads, idempotent replay and READY through
COMPLETED transitions. Source tree bytes, protected typed tables and non-target generic
state/revisions/events stay unchanged. Task completion does not create Evidence or personal mastery.

CLI discovery, common subprocess and network entry points are patched to fail during the tested
flow. This proves the controlled code path has no such dependency; it is not an OS sandbox or
uninstall test. No provider configuration is supplied. Task/idempotency tables are excluded from
the protected-state snapshot, so the test does not claim all other idempotency records unchanged.

## Deferred boundaries

No plugin marketplace, arbitrary Skill execution, multi-agent runtime, real provider invocation,
production Feishu/GitHub write, ATS action or legacy cutover is implied. Future adapter contracts
must preserve canonical truth and user authority. L2 preview is not execution consent.
