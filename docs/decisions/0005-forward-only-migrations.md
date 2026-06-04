# 0005. Forward-only Alembic migrations

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

Every schema change ships as an Alembic migration from commit one. Alembic generates a
`downgrade()` for each, implying migrations are reversible. In practice, downgrades for anything
beyond trivial column adds are rarely correct: dropping a column loses data, and reversing a data
migration is often impossible. A `downgrade()` that looks runnable but silently destroys data is a
trap during an incident.

## Decision

We will treat migrations as **forward-only**. Generated `downgrade()` bodies are replaced with a
`raise NotImplementedError` (enforced by our `script.py.mako` template), making the intent explicit
and failing loudly if anyone runs one. Rolling back a bad migration means rolling forward with a
new corrective migration, not downgrading. Applied migrations are never edited.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Forward-only (chosen) | Honest about reversibility; no data-loss trap; matches how prod rollbacks actually happen | No one-command "undo" in dev | — |
| Maintain real downgrades | Symmetric dev ergonomics | Significant effort to keep correct; false confidence; many are impossible | Cost and risk outweigh the rare dev convenience |
| No migrations (create_all) | Simplest | No schema versioning; impossible to evolve a deployed DB safely | Unacceptable for anything deployed |

## Consequences

Easier: migrations stay honest; no one trusts a downgrade that would corrupt data. Harder: to undo
a change in development you roll forward or rebuild the local DB (cheap — it reseeds in seconds).
We give up reversible migrations in exchange for not shipping a dangerous false affordance.

## References

- `CLAUDE.md` §6 (migrations forward-only)
- Code: `alembic/script.py.mako`, `alembic/versions/`
