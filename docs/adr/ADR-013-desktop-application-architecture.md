# ADR-013: Desktop Application Architecture

**Status:** PROPOSED

## Context

The product needs a Windows-first local desktop workspace while keeping Career Core
portable and testable outside the UI process.

## Decision

Use Tauri 2 for desktop/window/sidecar/native lifecycle, React + TypeScript + Vite
for the primary UI, and a Python sidecar for Career Core and local services.
Business logic does not move into Rust.

## Alternatives

- Electron with an embedded Node backend
- Browser-only UI with manually launched Python service
- Native Rust implementation of Career Core

## Consequences

The release pipeline must package a Python sidecar and manage its lifecycle. The
frontend and backend remain independently testable and replaceable.

## Rollback

The React app and Python API can run without Tauri during development; another shell
can replace Tauri without changing Core contracts.

