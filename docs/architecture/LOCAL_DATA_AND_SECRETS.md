# Local Data and Secrets

## Application data

`AppPaths` resolves an OS-specific application data root, with `ACH_DATA_DIR` as an
explicit development/test override. It keeps these locations separate:

- `career_harness.db`: canonical new-system SQLite database
- `artifacts/`: ordinary content-addressed artifacts
- `backups/`: verified backup sets
- `browser-sessions/`: credential/session material, never an ordinary artifact
- `logs/`: redacted operational logs

Creating these directories does not perform a legacy canonical cutover.

## Secrets

Core depends on a `SecretProvider` boundary. P0F includes an environment-backed
provider using `ACH_SECRET_<NAME>` variables and a redacting `SecretValue` wrapper.
No secret value is persisted or logged. A future OS Keychain implementation can
replace this provider without changing Core.

## Backup contract

A backup directory contains a SQLite online backup, copied content-addressed
artifacts, and `backup_manifest.json` with hashes. Verification requires every hash
and SQLite `PRAGMA integrity_check` to pass. Restore refuses existing targets and
writes into a separate location. Backup medium and retention remain user decisions.

