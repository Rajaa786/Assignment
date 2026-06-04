# Performance — where it matters, and why it feels fast

The persona is one HR manager browsing 10,000 employees. Performance work is targeted at the
operations they actually do, not micro-optimized everywhere. Measure first; the only optimizations
here are the ones that change the felt experience.

## Data layer

- **Integer minor units for money.** Salaries are integers, so `SUM`/`AVG`/`MIN`/`MAX` are exact
  and fast, and sorting/filtering by salary hits an index instead of doing decimal math (`ADR-0006`).
- **USD normalized on write.** `base_salary_usd_minor` is computed once when a record is written and
  **indexed**, so cross-country comparisons, sorts, and salary-range filters never recompute FX.
- **Indexes match the real query shapes.** Single-column indexes on `department`, `country`, `level`,
  `base_salary_usd_minor`, `last_name`, `email`, `deleted_at`, plus a composite
  `(country, department, level)` for the analytics group-bys.
- **SQLite WAL** in dev gives concurrent reads; production swaps to PostgreSQL via one
  `DATABASE_URL` (`ADR-0002`).

## List endpoint (the most-used screen)

- **Cursor (keyset) pagination** (`ADR-0007`): each page is an indexed range scan, not a deep
  `OFFSET`, so page 200 is as fast as page 1 and pages stay stable as data changes.
- **`limit + 1` look-ahead** decides "is there a next page?" without a second query; a separate
  `COUNT` supplies the total for display.
- The browser **never receives 10,000 rows** — only one page (default 25/50, max 200, enforced
  server-side).

## Analytics

- Each analytics call does **one projected scan** (four columns: the three dimensions + USD salary)
  and computes summary, per-dimension stats, the distribution histogram, and pay-equity gaps in
  pure Python. At 10k rows this is a few milliseconds and keeps the aggregation logic unit-testable
  with exact assertions. Aggregation is server-side; the client gets pre-aggregated buckets, never
  raw rows (`CLAUDE.md` §9). If the dataset grew an order of magnitude, these move to SQL
  `GROUP BY` + window-function medians with no API change.

## Seed

- 10,000 employees insert via a **single bulk statement in one transaction** — **~0.8s locally**,
  well under the 10-second budget. No per-row `add`/`commit` loop.

## Frontend

- **TanStack Query** caches list/analytics for 30s, dedupes in-flight requests, and keeps previous
  data while paging, so navigation feels instant; mutations invalidate only the affected keys.
- **Debounced search** (300ms) avoids a request per keystroke.
- Charts render **pre-aggregated buckets** from the analytics endpoints — the dashboard never holds
  10k rows in memory.

## The Q&A safety/perf bounds

Generated SQL runs read-only with a **1000-row cap** and (in production) a statement timeout, so an
expensive or pathological query can't hurt the database; repeated questions are served from a
session cache without re-prompting the model.
