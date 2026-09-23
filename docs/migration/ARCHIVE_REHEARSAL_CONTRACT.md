# Legacy archive and rehearsal contract

Frozen with shared contract 0.17.0 / D-027. Reversible local preservation and
disposable Core rehearsal are authorized by the overnight goal. No canonical cutover.

## Source and storage

- Reuse inventory manifest v1; no parallel legacy business domain.
- Legacy is read-only, including fixtures. Reject links/reparse points and unsafe
  path components; verify source size, mtime and hash against inventory. Compare
  complete source metadata signatures before/after real operations.
- Reuse AppPaths and its content-addressed artifacts store. Do not create another
  Data Root or change the production DB. Raw data/indices stay outside Git. Store
  inventory and archive index as artifacts so backup/restore includes provenance.
- Bind every batch to the hash of its exact serialized inventory bytes. Each index
  entry records relative path, size, original mtime, hash, source category/class,
  disposition/reason, archive location and candidate authority. Derive archive
  locations from hashes, never legacy-controlled destination paths.
- Same hash deduplicates bytes, not source paths. Different hashes remain distinct
  snapshots. Basename similarity never selects truth. Verify existing digest files;
  corruption fails loud. No runtime fallback to legacy paths or Excel calculations.

## Classification and reconciliation

- Exclude agent_radar_test_workspace from canonical migration with explicit records.
  Credential/session/key/profile paths never enter ordinary archive.
- Extension alone cannot establish public content. Credential markers are excluded;
  uncertain mixed/config/container content is deferred until inspected. Personal
  coding material is personal evidence, never market evidence.
- Report logical key/same hash, different hashes, cross-path byte duplicates,
  snapshot/version-family candidates and inspected archive-member duplicates.
  Unproven derived-copy relationships remain candidates, not asserted identities.
- Every source has preserved/excluded/deferred disposition. Report all remaining
  dependencies on Legacy; do not silently drop deferred material.
- Preserve literal source classes. A/B/C/D have no upgraded authority without a
  documented source definition. Missing values remain unknown. A supporting document
  does not prove its claims true; no frequency-based fact promotion.

## Disposable Core import

- Import explicit archived entries using existing Artifact, Source, SourceSnapshot
  and EvidenceRef tables with deterministic namespace-derived IDs. Historical source
  locators describe origin; actual bytes resolve in the new artifact store.
- Pin exact index/inventory digests in reports. Preserve original mtime separately
  from capture time. Same input produces identical rows; reimport is idempotent.
  Conflicting existing rows fail rather than overwrite.
- Additional structured domain mappings need explicit tested source mappings.
  Historical market interview accounts are not personal Interview appointments.
  Archive/counts alone never create Fact, Opportunity, UserPriority, Official Graph,
  mastery or MarketBinding. Unresolved mappings remain deferred.
- Use a dedicated disposable DB and refuse the configured production DB. Validate
  source counts, FKs, exact provenance, bytes/hash and DB integrity. Rebuild a second
  fresh DB, compare deterministic logical output, and validate repeated import.
  Delete only explicitly created disposable databases when needed.
- Back up DB plus complete artifact/index set, restore into absent targets, and
  verify hashes, rows and provenance again. Backup alone is not acceptance.

## Truth and projection

Archive proves preservation only. Staging read models explicitly say historical /
unconfirmed; they cannot masquerade as confirmed career state. Web/Feishu consume
Core read models or explicit staging reports, never UI SQL. Canonical cutover needs
resolved authority and explicit user approval. External Feishu writes have a separate
credential/permission gate.
