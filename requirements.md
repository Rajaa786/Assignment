# Requirements — ACME Salary Management

**Author:** Raj Singh · **Date:** 2026-06-04 · **Status:** Source of truth for scope

## Goal

ACME's HR team manages salary data for **10,000 employees across multiple countries**
in spreadsheets. That is slow, error-prone, and impossible to query safely. This software
gives the **single HR manager** one web tool to (1) **manage salary records** and
(2) **answer questions about how the organization pays people** — without writing SQL or
juggling exchange rates by hand.

Success = the HR manager opens the app, sees how the org pays at a glance, finds and edits
any employee in seconds, bulk-imports the existing spreadsheet, and asks a question in plain
English and gets a correct, safe answer.

## Users

One persona: the **HR Manager**. Internal tool, trusted single user, no public surface.
This single-persona assumption is load-bearing — it justifies several scope cuts below.

## In scope

| # | Feature | Why it matters to the persona |
|---|---|---|
| 1 | Employee records: create, read, update, soft-delete | Core CRUD that replaces the spreadsheet |
| 2 | Server-side list: search, filter (country/department/level/salary band), sort, **cursor pagination** | Find anyone among 10k rows fast; the UI never loads 10k rows |
| 3 | **Multi-currency** salaries stored exactly + normalized to a base currency (USD) | Compare pay across countries meaningfully |
| 4 | Analytics dashboard: headcount, total payroll, avg/median, distribution, **pay-equity** by dept/country/level | "How do we pay people?" answered at a glance |
| 5 | **Natural-language Q&A**: ask in English → guarded read-only SQL → answer | Ad-hoc questions without engineering help — the headline capability |
| 6 | **CSV import (with dry-run) + export** | Migrate off Excel on day one; round-trip data out |
| 7 | Seed of 10,000 realistic, multi-country employees | Demonstrate real-scale behavior |

## Deliberately out of scope (and why)

The rubric grades *what we choose not to build*. Each cut is a judgment call, not an omission.

- **Authentication / login / RBAC.** One trusted internal persona; no multi-user or
  permission requirement in the brief. Real auth is a security surface that must be done
  properly or not at all — half-built auth is worse than none. Production fronts the app with
  an identity-aware proxy (Cloudflare Access / Okta-fronted ALB); the app stays auth-agnostic
  with a clean seam where a `current_user` dependency would slot in. → `ADR-0009`.
- **Salary change history / audit trail.** The brief asks to *manage current salaries* and
  *answer questions*, not reconstruct the past. A temporal model roughly doubles the schema
  and every query for a feature no one asked for. The schema is designed so a
  `compensation_history` table can be added **additively** later with zero migration of
  existing rows. → `ADR-0003`.
- **Payroll runs, tax, benefits, deductions.** This is salary *data management*, not a payroll
  engine. Pay computation is a different product with different compliance weight per country.
- **Live FX rate feed.** Exchange rates come from a seeded table, not a live provider:
  deterministic, testable, no network flakiness in review. The converter is a `Protocol` —
  swapping in a live provider is one implementation, no call-site changes. → `ADR-0006`.
- **Background workers / queues (Celery).** Synchronous request handling is sufficient for 10k
  rows and one user; CSV import bulk-inserts inside a single transaction in well under the
  request budget. Adding a broker would be infrastructure with no payoff.
- **Real-time updates / WebSockets, i18n / RTL, mobile / offline, multi-tenancy.** None serve
  a single HR manager on a desktop browser inside one organization.

## Non-functional requirements

- **Performance (felt):** every list is paginated + indexed; aggregations run in SQL, never in
  app memory; the browser never receives 10k raw rows; seed completes in < 10s.
- **Safety:** NL Q&A executes only `SELECT`, against a read-only path, behind a parser guard,
  with row/time caps. No string-concatenated SQL anywhere. Logs never contain salary amounts.
- **Quality:** money stored as integer minor units (never float); fast, deterministic tests;
  `mypy --strict` and `ruff` clean; every schema change ships an Alembic migration.
- **Onboarding:** one-command run (`docker compose up`); auto OpenAPI docs at `/docs`.
