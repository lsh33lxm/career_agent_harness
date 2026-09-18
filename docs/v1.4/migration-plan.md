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
| M2 | Add Opportunity/Watchlist and Capability records | No automatic legacy conversion | Drop new empty tables before release. |
| M3 | Add Project/Context records | No filesystem scan on migration | Drop new empty tables; artifacts untouched. |
| M4 | Compatibility transform for `OpportunityState.WATCHING` | Explicit rehearsal report; user approval if real records exist | Preserve original revisions; reverse mapping. |
| M5 | Resume/Application/Outcome vertical slice | Additive records with evidence refs | Tombstone new records; retain audit. |
| M6 | Legacy import (future gate) | Approved manifest only | Restore verified pre-import backup. |

## Required migration tests

- Fresh database upgrades to head.
- Upgrade is repeatable through bootstrap helper.
- Existing `0001_foundation` data survives every additive migration.
- Foreign keys prevent deleting referenced evidence/official graph versions.
- Official graph upgrade does not overwrite personal capability state.
- Suggested priority updates do not modify user priority.
- Downgrade is tested only on disposable databases; production rollback uses backup/restore.

## Approval gates

`NEEDS USER APPROVAL`: destructive migration, real legacy cutover, retention, encryption, backup
medium, or final opaque ID format. No current Wave 0 change crosses these gates.

