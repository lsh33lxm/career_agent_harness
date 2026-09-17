# ADR-016: New Application Repository vs Legacy Workspace

**Status:** PROPOSED

## Context

Agent Radar is a live historical research/data workspace with multiple possible data
roots and no confirmed canonical authority.

## Decision

Treat `agent_rader` as a preserved, read-only research and migration source. Build
`agent-career-harness` as the formal software repository with Git, locks, tests,
migrations, and explicit import/reconciliation boundaries.

## Alternatives

- Convert the legacy workspace in place
- Copy the entire legacy workspace into the new Git repository

## Consequences

Migration requires inventory, hashes, identity mapping, reconciliation, approval,
and rollback proof. There is no bidirectional write path.

## Rollback

The new repository can be discarded without modifying legacy files.

