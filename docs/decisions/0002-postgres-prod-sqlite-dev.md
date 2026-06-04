# 0002. PostgreSQL in production, SQLite in local dev

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

A reviewer must be able to clone and run this in minutes, with no database server to install.
But production needs concurrency, a managed backup story, and a real query planner for the
analytics group-bys over 10k rows. These two needs pull in different directions: zero-setup for
review vs. robustness for production.

SQLAlchemy abstracts the dialect, so the same ORM models and queries can target both — provided
we avoid dialect-specific SQL and choose the engine from configuration rather than hard-coding it.

## Decision

We will use **SQLite for local development and tests** and **PostgreSQL (Neon free tier) in
production**. The driver is selected from a single `DATABASE_URL` — there is exactly **one engine
factory**, never a branch on environment. Queries stay portable (no raw dialect SQL); the one
place dialects differ that we touch — `PRAGMA journal_mode=WAL` for SQLite — is applied only when
the URL is SQLite, via a connection event.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| SQLite dev / Postgres prod (chosen) | Zero-setup review; prod parity via one URL; tests run in-memory and fast | Must avoid dialect-specific SQL; two engines to smoke-test | — |
| Postgres everywhere (incl. dev) | Perfect parity | Reviewer must run Postgres (or Docker) before anything works; slower, less friendly tests | Hurts onboarding and test speed for little gain at this scale |
| SQLite everywhere (incl. prod) | Simplest | Single-writer, weak concurrency, no managed ops/backup | Unacceptable for a "production" deployment |

## Consequences

Easier: `git clone && pip install && alembic upgrade head` works with no DB server; tests use an
in-memory SQLite and stay fast and isolated. Harder: we must keep queries dialect-neutral and
smoke-test against Postgres before deploy; median is computed with portable SQL (window
functions) available in both. We accept SQLite's single-writer limit in dev (a non-issue for one
developer) and rely on Postgres for production concurrency.

## References

- `CLAUDE.md` §2 (stack), §6 (WAL pragma, migrations)
- Related: `ADR-0001` (FastAPI), `ADR-0005` (forward-only migrations)
