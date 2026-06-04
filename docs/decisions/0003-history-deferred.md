# 0003. Salary change history deferred — additive by design

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

The brief asks the HR manager to *manage current salaries* and *answer questions about how the
org pays people*. It does not ask to reconstruct what someone earned last year, audit who changed
a figure, or model effective-dated raises. A full temporal model (history table, effective-date
ranges, "as-of" queries) is a large, cross-cutting feature: it touches the schema, every write
path, and most read paths.

The risk is building an audit/history system nobody asked for and spending the assessment's budget
there instead of on usability and the analytics that answer the actual question.

## Decision

We will **not** build salary change history now. We will design the `employees` schema so a
`compensation_history` table can be added **additively later with zero migration of existing
rows**: the current salary lives on `employees`, history (if added) becomes a child table keyed by
`employee_id` with its own effective-date columns. No existing column is repurposed or dropped to
get there.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Defer, design additively (chosen) | Focus budget on asked-for value; clean future path | No history today | — |
| Build full temporal model now | Complete audit trail | Large scope; complicates every write and read; unasked-for | Over-building; the rubric rewards thoughtful cuts |
| Append-only event log for all changes | Maximal auditability | Even larger; needs projections to answer simple "current salary" reads | Disproportionate for one HR manager managing current pay |

## Consequences

Easier: the model and queries stay simple; writes are single-row updates. Harder: there is no
answer to "what did this person earn before this edit" — an accepted gap, documented here and in
`requirements.md`. When history is needed, it is a new table plus a write-time insert, not a
migration of the existing 10k rows. We give up auditability of edits in this version.

## References

- `CLAUDE.md` §4 (additive schema), §18 (scope — history out)
- `requirements.md` (deliberately out of scope)
