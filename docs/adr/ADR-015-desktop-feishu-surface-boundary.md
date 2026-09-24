# ADR-015: Desktop and Feishu Product Surface Boundary

**Status:** PROPOSED

## Context

The product needs a rich local workspace and a convenient mobile/review companion
without creating competing truth stores.

## Decision

Desktop is the primary product workspace. Feishu is a rebuildable companion
projection and command inbox. Career Core owns truth; neither surface writes storage
directly.

## Alternatives

- Feishu as the primary human workspace and canonical data store
- independent desktop and Feishu databases with bidirectional synchronization

## Consequences

Feishu integration requires outbox, inbox, expected revisions, durable cursors,
conflict review, and dead letters. Desktop remains useful when Feishu is unavailable.

## Rollback

Disable or rebuild Feishu projections without affecting Career Core or Desktop.

