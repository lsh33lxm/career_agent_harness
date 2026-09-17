# Legacy Inventory Baseline

**Observed:** 2026-09-18

**Status:** CANDIDATE - NEEDS USER APPROVAL

The read-only importer scanned the complete legacy Agent Radar workspace. Generated
details are intentionally ignored by Git because filenames and structure may contain
personal or historical working data.

## Result

- Source files hashed: 2,210
- Source bytes: 360,355,195
- Snapshot candidates: 286
- Workbooks with structural metadata: 11
- Skipped symlink/reparse entries: 0
- Candidate reconciliation records: 332
- Approved entities: 0
- Canonical source selected: no

## Read-only verification

The inventory command:

1. captured a path/size/mtime metadata signature before scanning;
2. streamed every source file through SHA-256 without writing to the source;
3. wrote the candidate manifest in the new repository;
4. captured the source metadata signature again and required equality;
5. re-read every manifest source file and required its SHA-256 to match.

The command completed without a metadata-signature change or hash mismatch. This is
evidence that the importer did not modify observed legacy files; it does not prove
which legacy root is canonical.

## Generated local outputs

- `LEGACY_IMPORT_MANIFEST.json`
- `LEGACY_RECONCILIATION_REPORT.md`

Both files are regenerated locally and excluded from Git. The reconciliation report
marks all unresolved filename/hash conflicts `deferred`.

