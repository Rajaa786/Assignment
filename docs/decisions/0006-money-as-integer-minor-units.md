# 0006. Money stored as integer minor units + ISO 4217 code

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

This is a salary system: every number that matters is money, across 11 currencies with
different minor-unit conventions (USD has cents, JPY has none). Floating-point cannot represent
most decimal money exactly (`0.1 + 0.2 != 0.3`), and those errors compound across 10,000 rows
and aggregate queries. We also need cross-country comparison, which means a base-currency
normalization that must round predictably.

The forces: correctness (no drift), portability across SQLite and PostgreSQL, fast aggregation
in SQL, and a representation a reviewer immediately trusts.

## Decision

We will store every monetary value as an **integer count of minor units** (e.g. cents) in a
`*_minor` column, paired with an **ISO 4217 currency code** column. A `Money(amount: Decimal,
currency: Currency)` value object owns all arithmetic and the major⇄minor conversion, using each
currency's exponent. A normalized `base_salary_usd_minor` is computed once on write (via a
`CurrencyConverter` protocol) and indexed, so comparisons and sorts never recompute FX. The
converter is an interface; the rate source (a seeded table now, a live feed later) is swappable.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Integer minor units + ISO 4217 (chosen) | Exact; fast integer aggregation; portable; trustworthy | Manual major⇄minor at the edges; must track per-currency exponent | — |
| `Numeric(18,4)` decimal column | Exact; arithmetic in SQL reads naturally | Heavier than int; mixing scales across currencies still needs the exponent; SQLite stores `NUMERIC` loosely | Acceptable fallback, but int is simpler and faster at this scale |
| `FLOAT`/`REAL` | Simplest to write | Inexact for money — silent drift in aggregates | Disqualified on correctness alone |

## Consequences

Easier: aggregates (`SUM`, `AVG`) run on integers and stay exact; the `Money` type makes float
math on money impossible by construction; the normalized column makes cross-country analytics a
single indexed scan. Harder: the API and CSV layers must convert between major units (what humans
type) and minor units (what we store), and every currency's exponent must be known — both
centralized in the `Currency`/`Money` value objects so the conversion exists in exactly one place.
We give up the convenience of reading raw amounts straight off the row.

## References

- `CLAUDE.md` §4 (data modeling), §3 (domain value objects)
- Code: `app/domain/money.py`, `app/domain/currency.py`, `app/domain/currency_converter.py`
