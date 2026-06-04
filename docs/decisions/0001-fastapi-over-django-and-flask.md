# 0001. FastAPI over Django + DRF and Flask

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

This is a JSON API for an internal single-page app: employee CRUD, server-side
list/filter/pagination over 10k rows, SQL-backed analytics, CSV import/export, and a
natural-language Q&A endpoint that calls an LLM and validates generated SQL. There is no
server-rendered HTML, no session/template story, and the role is explicitly a Python/AI one
where typed request/response contracts and auto-generated API docs carry real weight for the
reviewer's developer experience.

The forces: I want strict request/response validation at the edge, first-class typing
(`mypy --strict`), low ceremony for a small surface, and OpenAPI docs for free so onboarding is
"open `/docs`." I do **not** need an admin site, an opinionated ORM-bound template stack, or
multi-app project scaffolding.

## Decision

We will use **FastAPI** for the API layer, with Pydantic v2 for transport schemas and SQLAlchemy
2.0 (used directly, not via a framework ORM). Dependency injection via `Depends` gives us
testable services without a DI framework.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| FastAPI (chosen) | Pydantic validation, free OpenAPI, async, tiny surface, DI via `Depends` | Fewer batteries (assemble auth yourself) | — |
| Django + DRF | Admin, ORM, auth, migrations included | Heavyweight for a JSON-only API; DRF serializers weaker-typed than Pydantic; admin tempts scope creep we explicitly cut | Batteries we won't use; admin would undercut the "build the UI" requirement |
| Flask | Minimal, flexible | Validation, schema docs, and typing are all manual; more wiring to reach the same contract guarantees | Hand-rolling what FastAPI gives for free, with weaker types |

## Consequences

Easier: typed contracts and OpenAPI come for free; services are trivially unit-testable by
overriding `Depends`. Harder: we own concerns Django would have shipped — notably auth (cut
deliberately, see `ADR-0009`) and any admin tooling (we build the UI instead). We accept FastAPI's
younger ecosystem relative to Django; for this surface that is not a constraint.

## References

- `CLAUDE.md` §2 (locked stack), §3 (layered architecture)
- Related: `ADR-0002` (database), `ADR-0009` (auth deferred)
