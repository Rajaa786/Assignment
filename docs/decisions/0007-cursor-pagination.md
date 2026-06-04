# 0007. Cursor (keyset) pagination over offset for list endpoints

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

The employee list is the most-used screen and runs over 10,000 rows that change while the HR
manager browses (creates, edits, soft-deletes). Two problems with offset pagination at this scale:
deep offsets (`LIMIT 50 OFFSET 9000`) force the database to scan and discard thousands of rows, and
rows shifting between page loads cause items to be skipped or shown twice.

We need stable pages, cheap "next page," and arbitrary sort orders (by name, salary, hire date)
that still paginate correctly.

## Decision

We will use **keyset (cursor) pagination**. The list orders by the chosen sort column plus `id` as
a tiebreaker, and the next page is fetched with `WHERE (sort, id) > (last_sort, last_id)`. The
cursor is an **opaque base64 token** wrapping `{sort_value, last_id}`; clients pass it back
verbatim. The response envelope is `{ items, next_cursor, total }` with a default page size of 50
and a server-enforced max of 200. We fetch `limit + 1` rows to know whether a next page exists
without a second query.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Keyset cursor (chosen) | O(log n) per page via index; stable under writes; scales to 10k+ | No "jump to page N"; cursor must encode the sort key | — |
| Offset/limit | Trivial; supports page jumps | Deep-offset scans get slow; rows shift → skips/dupes | Poor felt performance and correctness at scale |
| Fetch-all + client paginate | Simplest server | Ships 10k rows to the browser; defeats the point | Violates the "never send 10k rows" rule |

## Consequences

Easier: pages stay fast and stable as data changes; the index on the sort column does the work.
Harder: there is no random "go to page 7" (the UI offers next/previous and filtering instead), and
each sortable column must be indexed and its value encodable in the cursor — so the set of sortable
fields is deliberately small (`id`, `name`, `salary`, `hire_date`). `total` is still returned for
display, via a separate count query. We give up arbitrary page jumps in exchange for correctness
and speed.

## References

- `CLAUDE.md` §5 (cursor pagination, response shape), §9 (performance)
- Code: `app/core/pagination.py`, `app/repositories/employee_repository.py`
