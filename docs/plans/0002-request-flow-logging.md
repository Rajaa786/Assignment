# Plan: Simple request-flow logging across the non-QA APIs (+ commit)

## Context

Part 1 (done, green, **uncommitted**) gave `/ask` a staged trace. The rest of the app is
dark at the app level: employees CRUD, analytics, and CSV import/export emit no logs, and
4 of 5 error handlers swallow silently. The user wants the **same kind of visibility**,
kept **simple**: plain `logger.info` as the request proceeds through the service functions
and `logger.error`/`warning` on failures — "just like print logs." Two explicit
constraints from the user:

- **Don't touch uvicorn.** Its access log keeps printing as-is. No `--no-access-log`, no
  format change, no access-log middleware.
- **Nothing major.** No new infrastructure — just info/error logs along the flow, plus
  logging the handled errors (confirmed: yes).

**Intended outcome:** hitting any endpoint prints app-level `logger.info` lines showing
the operation as it runs (auto-tagged with `request_id` from the existing middleware), and
errors print with their stable code — alongside uvicorn's untouched access line.

## Scope

**In:**
1. **Service-layer flow/operation logs** (info) — logs live in the services (where the
   logic is; routers stay thin per §3), so they auto-carry `request_id` via structlog
   contextvars. One clear line per operation; CSV import (which has stages) gets a
   start + complete.
2. **Handled-error logging** in `app/core/errors.py` — the 3 currently-silent handlers.
3. **§8 PII**: log employee **ids, operations, counts, field names** — never amounts.

**Out / deferred (per "nothing major"):**
- No access-log middleware; **uvicorn's access log stays**.
- **Slow-query log (§14)** — was in an earlier draft, but it's an engine-level
  `before/after_cursor_execute` listener = the infra the user asked me to skip now.
  **Flagged as a known §14 gap**; ~15 lines to add on request later.
- No config changes. `LOG_LEVEL` stays at its **info** default (the user's "keep log
  level to info" — already the default, nothing to change).

## Events (service → event → fields; all info unless noted)

`employee_service.py` (+ `logger = get_logger(__name__)`):
- `employee_created` (`employee_id`, `country`, `department`)
- `employee_updated` (`employee_id`, `fields=sorted(changes)`) — field **names**, not values
- `employee_deleted` (`employee_id`)
- `employee_fetched` (`employee_id`)
- `employees_listed` (`count=total`, `limit`)

`analytics_service.py` (+ logger): `analytics_summary_computed`,
`analytics_by_dimension_computed` (`dimension`), `analytics_distribution_computed`,
`analytics_pay_equity_computed`.

`csv_service.py` (+ logger): `csv_import_started` (`dry_run`, `size_bytes`),
`csv_import_completed` (`dry_run`, `total`, `valid`, `failed`, `inserted`),
`csv_export_completed` (`row_count`).

`core/errors.py` (change ignored `_: Request` → `request`, add `path`/`method`):
- `handle_app_error` → `app_error` (`code`, `status_code`) — `error` if status ≥ 500 else `warning`
- `handle_request_validation_error` → `request_validation_failed` (`errors`=sanitized loc/msg/type), `warning`
- `handle_invalid_cursor_error` → `invalid_cursor`, `warning`
- `handle_unexpected_error` — already logs `unhandled_exception` with `exc_info`; leave it

## Files

- Modify: `app/services/employee_service.py`, `app/services/analytics_service.py`,
  `app/services/csv_service.py`, `app/core/errors.py`, `CLAUDE.md` (§16 row 0014).
- New (1): `docs/decisions/0014-operation-and-flow-logging.md` (short Nygard ADR: app-wide
  operation/flow + handled-error logging convention; alternatives = stay silent / access-log
  middleware / per-router logs; note the deferred slow-query log and untouched uvicorn).
- **Not touched:** `middleware.py`, `database.py`, `main.py`, `Dockerfile`,
  `docker-compose.yml`, `logging.py`.

## Tests (ship with code, `structlog.testing.capture_logs`; extend existing modules)
- `test_employees_api.py`: `employee_created` on create (id present); `employee_deleted`
  on delete.
- analytics test (extend if present, else minimal): `analytics_summary_computed` on
  `GET /analytics/summary`.
- `test_imports_api.py`: `csv_import_completed` carries the right counts (dry-run).
- Error logging: `app_error` (code `employee.not_found`) on a 404;
  `request_validation_failed` on a bad POST body.

## Verification
1. `cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . &&
   .venv/bin/mypy app && .venv/bin/pytest -q` — all green (§15).
2. Optional render check (json+info): confirm an `employee_created` / `app_error` line
   prints as JSON with `request_id`.

## Commit (final step — two conventional commits on `main`, no push)
Inspect `git status` + `git diff` first; commit only intended changes (flag anything
pre-existing/unrelated). Tests in the same commit as code (§15); full gate green before
each. Commit Part 1 first (already green), then implement + commit Part 2 — so `CLAUDE.md`
and any shared files split cleanly without interactive `git add -p`.
1. `feat(observability): request-scoped structured tracing for the Q&A path` — Part 1
   (qa_service, client `describe()`, factory, logging `format_exc_info`, ADR-0013,
   CLAUDE.md 0013 row, the two test files).
2. `feat(observability): operation & flow logging across employee/analytics/CSV APIs` —
   Part 2 (the 3 services, errors.py, ADR-0014, CLAUDE.md 0014 row, new test assertions).

**No push** (push triggers GHCR image builds — the user's call). Committing to `main` per
repo convention (all 17 commits are on main; solo assessment, no PR history).
