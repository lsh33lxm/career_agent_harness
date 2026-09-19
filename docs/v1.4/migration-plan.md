# v1.4 Migration Plan

## Principles

1. Migrations are additive and reversible while v1.4 slices are introduced.
2. Existing foundation tables remain intact; new domain tables reference stable IDs.
3. Generic JSON state is compatibility storage, not the default for new queryable domain data.
4. No legacy Agent Radar record is imported or declared canonical without approved reconciliation.
5. Official capability ontology and personal overlay use separate storage and upgrade paths.
6. Backups cover every new SQLite table automatically; new artifact directories must be added to
   backup manifests before use.

## Planned sequence

| Stage | Change | Data action | Rollback |
| --- | --- | --- | --- |
| M0 | Align in-code repository contract | None | Revert code commit. |
| M1 | Add shared relational identity/priority/event support if required | Empty additive tables/columns | Alembic downgrade on rehearsal DB. |
| M2a | Add typed Opportunity/Watchlist/Priority records | Completed in `3f102f0`; no automatic legacy conversion | Tested downgrade to 0001 on disposable DB. |
| M2b | Add Capability records | Completed in `2b7901d`; no automatic seed/import | Tested downgrade to 0002 on disposable DB. |
| M3a | Add Project Evidence records | Completed in `158547b`; no filesystem scan or legacy import | Tested downgrade to 0003 on disposable DB. |
| M3b | Add Context Manifest records | Completed in `95d3df6`; bounded selection/provenance metadata only | Tested downgrade to 0004 on disposable DB. |
| M3c | Guard Personal Capability identity across revisions | Completed in `61b5a4f`; no data rewrite, upgrade fails loud on historical drift | Tested `0005 -> 0006 -> 0005 -> 0006` on disposable DB. |
| M4 | Compatibility transform for `OpportunityState.WATCHING` | Explicit rehearsal report; user approval if real records exist | Preserve original revisions; reverse mapping. |
| M5 | Resume/Application/Outcome vertical slice | Additive records with evidence refs | Tombstone new records; retain audit. |
| M6 | Legacy import (future gate) | Approved manifest only | Restore verified pre-import backup. |

## Required migration tests

- Fresh database upgrades to head.
- Upgrade is repeatable through bootstrap helper.
- Existing `0001_foundation` data survives every additive migration.
- Foreign keys prevent deleting referenced evidence/official graph versions.
- Official graph upgrade does not overwrite personal capability state.
- One `personal_state_id` cannot change candidate/capability identity across revisions; existing
  drift blocks upgrade for explicit reconciliation rather than being silently rewritten.
- Released official graph rows are append/update/delete protected; new releases are assembled in
  one deferred-FK transaction and sealed by inserting the graph version last.
- Suggested priority updates do not modify user priority.
- Opportunity proposal, user decision, canonical record, SuggestedPriority and UserPriority use
  distinct tables and DB authority checks.
- Project scan manifests pin the exact scope revision; evidence pins a non-empty immutable manifest.
- Project Capability state and relational basis commit atomically through a deferred FK; evidence
  and user Approval references are exact, scoped and immutable.
- Context Manifest refs are ordered, counted, immutable and sealed parent-last; Project Evidence
  refs use exact revisions and no compiled/task/asset payload content is stored.
- Downgrade is tested only on disposable databases; production rollback uses backup/restore.

## Approval gates

`NEEDS USER APPROVAL`: destructive migration, real legacy cutover, retention, encryption, backup
medium, or final opaque ID format. No current Wave 0 change crosses these gates.
