# Legacy Agent Radar Migration Plan

**Source:** `D:\0.小红书投稿\小红书稿\9.15 三期\agent_rader`

**Source mode:** READ ONLY until an explicitly approved cutover.

## Stages

1. **Inventory:** enumerate allowed files without following links; record relative
   path, size, modified time, SHA-256, inferred category, and legacy key candidates.
2. **Candidate manifest:** generate `LEGACY_IMPORT_MANIFEST.json` in the new
   repository with source workspace, files/hashes, snapshot candidates, legacy keys,
   importer version, and generation time. It is evidence, not approval.
3. **Identity proposal:** map legacy keys to candidate opaque Core identities without
   mutating either source or Core truth.
4. **Reconciliation:** compare `work/`, `data/`, `codex/data/`, workbook metadata,
   manifests, configs, and snapshots. Record mismatches and dispositions as
   accepted, rejected, or deferred.
5. **Approval gate:** present `LEGACY_RECONCILIATION_REPORT.md`; unresolved authority
   and identity choices require user approval.
6. **Import rehearsal:** import only approved entities into a disposable database;
   verify counts, member IDs, hashes, provenance, mismatch handling, and rollback.
7. **Backup/restore rehearsal:** create a consistent DB backup plus artifact manifest,
   verify hashes, and restore into a separate location.
8. **Cutover:** only after explicit approval may an import become canonical.

## Read-only enforcement

- Resolve source and output paths before work begins.
- Reject any output located within the source workspace.
- Open source files only for reading; do not use legacy scripts or pipelines.
- Do not follow symlinks/reparse points outside the inventory boundary.
- Snapshot source metadata before and after importer tests and assert no observed
  size/modified-time changes.
- Write manifests, reports, databases, logs, and caches only beneath the new repo or
  an isolated temporary directory.

## Reconciliation record

Each record carries source path/hash, legacy key, proposed Core identity, mismatch
details, disposition (`accepted`, `rejected`, `deferred`), reason, actor, and time.
Deferred is the default when authority cannot be proven.

## Rollback

Before cutover, rollback means deleting a disposable new-system database and
generated artifacts; the legacy source remains unchanged. After a future cutover,
rollback requires a verified pre-cutover backup and an approved runbook not yet
defined in this phase.

