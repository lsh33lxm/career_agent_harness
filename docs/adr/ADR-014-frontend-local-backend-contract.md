# ADR-014: Frontend to Local Backend Contract

**Status:** PROPOSED

## Context

The desktop UI must communicate with a separately testable local service without
exposing it to the network or allowing unrelated local origins to issue commands.

## Decision

Use REST/JSON over `127.0.0.1`, a random release port, and an ephemeral per-launch
bearer token. Restrict origins and bind only localhost. Development may use explicit
local settings while preserving the same authentication contract.

## Alternatives

- Tauri invoke commands for all business operations
- fixed unauthenticated localhost port
- Unix socket/named pipe as the initial transport

## Consequences

API schemas must be typed and versioned. Tauri must securely pass port/token launch
configuration to the UI, and logs must redact tokens.

## Rollback

Transport can be replaced behind the typed client and API boundary without changing
domain commands.

