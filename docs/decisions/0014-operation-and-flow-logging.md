# 0014. Operation & flow logging across the API

- **Status**: Accepted
- **Date**: 2026-06-06
- **Deciders**: Raj Singh

## Context

ADR-0013 instrumented the `/ask` Q&A path, but every other endpoint was dark at the
application level: the employee CRUD, analytics, and CSV import/export services emitted no
logs, and four of the five exception handlers mapped errors to the response envelope
**without logging anything**. The only per-request line was uvicorn's built-in access log —
plain text, no `request_id`, no business outcome. When a reviewer (or the HR manager) hits
an endpoint, nothing in the structured logs shows what the request actually did or why a
4xx came back.

The fix needs to stay small and boring. The structured-logging plumbing already exists
(`get_logger`, the `request_id`-binding middleware); what was missing was simply *using*
it along the request flow.

## Decision

We will emit plain `logger.info` operation events from the **service layer** as a request
proceeds, and log every **handled error** in the exception handlers — reusing the existing
structlog setup so each line auto-carries `request_id`. Services own the events because
that is where the business logic lives (routers stay thin, §3):

- **employees**: `employee_created` / `employee_updated` / `employee_deleted` /
  `employee_fetched` / `employees_listed`.
- **analytics**: `analytics_summary_computed` / `analytics_by_dimension_computed` /
  `analytics_distribution_computed` / `analytics_pay_equity_computed`.
- **CSV**: `csv_import_started` → `csv_import_completed` (with counts) / `csv_export_completed`.
- **errors** (`app/core/errors.py`): `app_error` (4xx → warning, 5xx → error),
  `request_validation_failed` (with the sanitized field errors), `invalid_cursor`.

Per §8, these logs carry **employee ids, operation names, counts, and field names — never
salary amounts**. `employee_updated` logs `sorted(changes)` (the field *names* that
changed), not their values.

We deliberately **leave uvicorn's access log untouched** (it keeps printing) and add no
access-log middleware — the goal was visibility into the function flow, not a logging
framework. The **slow-query log** (§14) is acknowledged as a remaining gap and deferred:
it is an engine-level `before/after_cursor_execute` listener, out of scope for this small
change.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Service-layer operation logs + handler logs (chosen) | Small, boring, reuses existing setup; logs sit where the logic is; auto `request_id` | A handful of log lines to maintain; some duplication with uvicorn's access line | — |
| Stay on uvicorn's access log only | Zero code | No `request_id`, no business outcome, errors stay silent | The exact gap being fixed |
| App-level access-log middleware (+ disable uvicorn's) | One uniform structured access line per request | "Major" infra the user explicitly declined this round; changes the run command | Out of scope by request; revisit if needed |
| Log in routers instead of services | Routers see the HTTP request | Routers must stay thin (§3); business outcomes (counts) live in services | Wrong layer |

## Consequences

Easier: every endpoint now shows an `info` trail of what it did, correlated by
`request_id`, and handled 4xx/5xx errors are no longer silent — a 422 logs *which* fields
failed. Harder / given up: a little redundancy with uvicorn's access log (accepted —
they serve different readers), and read endpoints now log too (fine at one-HR-user scale).
The slow-query log (§14) and a unified access log remain deliberately deferred.

## References

- `CLAUDE.md` §3 (thin routers), §8 (no salary amounts), §14 (observability)
- Code: `app/services/employee_service.py`, `app/services/analytics_service.py`,
  `app/services/csv_service.py`, `app/core/errors.py`
- Related: `ADR-0013` (QA-path tracing — same convention, applied first)
