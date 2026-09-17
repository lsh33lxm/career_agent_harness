# Repository Agent Instructions

## Authority and phase

Read `AGENT_CAREER_HARNESS_PRD_v1.2.md` before architecture or implementation
changes. Its Hard Constraints, approved ADRs, and Core Contracts override local
preferences and external reference projects.

Current scope is P0F and approval-free P0B preparation. Do not start P1/P2 work,
production Feishu writes, real ATS submission, full resume automation, plugin
marketplaces, or multi-agent runtime work.

## Legacy boundary

`D:\0.小红书投稿\小红书稿\9.15 三期\agent_rader` is a read-only legacy system.
Never edit, rename, move, delete, format, clean, or run write-producing pipelines
there. Importers may inventory and hash it without following symlinks. All generated
manifests and reconciliation output belong in this repository.

## Required invariants

- Evidence != Fact != Signal != Decision != Outcome.
- ExtractedClaim != Fact; model and parser output require promotion.
- Workflow State != Business State.
- Opportunity != Application; Prepared != Submitted.
- Agents and adapters never approve their own proposals or own truth.
- Desktop and Feishu are clients/projections; Career Core owns business truth.
- SQLite is not legacy canonical truth before reconciliation and approved cutover.
- User controls identity, legal, work authorization, and final submission answers.

## Engineering workflow

1. Read `STATUS.md` and the relevant PRD sections.
2. Choose the smallest safe P0F/P0B task.
3. State affected files, security impact, and test plan before editing.
4. Keep changes typed, auditable, reversible, and narrowly scoped.
5. Run the fastest relevant test, update `STATUS.md`, and commit a focused change.
6. Record unapproved architectural choices as `PROPOSED` or `NEEDS USER APPROVAL`.

Never commit secrets, credentials, personal resumes, offers, browser profiles,
runtime databases, generated artifacts, or copied raw legacy data.

