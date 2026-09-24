# Engineering Decisions

This log records implementation choices. Architectural decisions that require user
approval remain `PROPOSED` and are detailed in `docs/adr/`.

## D-001 - Preserve PRD authority

**Status:** ACTIVE

**Context:** The repository begins from an integrated PRD with explicit precedence.

**Decision:** Keep `AGENT_CAREER_HARNESS_PRD_v1.2.md` unchanged at the repository
root and index it from `docs/prd/README.md` as the authoritative baseline.

**Alternatives:** Copy and edit the PRD under `docs/`; rewrite it into framework
documentation.

**Reason:** A single authoritative file prevents silent contract drift.

**Impact:** Proposed deltas must be recorded separately and approved.

**Rollback:** Remove the index; never rewrite history in the PRD itself.

## D-002 - Keep legacy access read-only

**Status:** ACTIVE

**Context:** Other processes may currently use the Agent Radar workspace.

**Decision:** Inventory with read-only metadata and streaming hashes only. Store all
outputs in the new repository and reject output paths inside the legacy root.

**Alternatives:** Normalize legacy files in place; copy all raw data into Git.

**Reason:** Prevents interference and preserves migration evidence.

**Impact:** Reconciliation is explicit and canonical cutover remains gated.

**Rollback:** The importer can be removed without changing any legacy asset.

## D-003 - Use project-local dependencies

**Status:** ACTIVE

**Context:** Foundation work requires reproducible tooling without system changes.

**Decision:** Use a repository-local Python virtual environment and npm lockfile.
Use the already installed Rust toolchain for Tauri validation.

**Alternatives:** Global package installation; speculative dependency installation.

**Reason:** Keeps the environment reversible and limits supply-chain surface.

**Impact:** Commands must run through the local environments.

**Rollback:** Delete ignored local environments and reinstall from lock/config files.

