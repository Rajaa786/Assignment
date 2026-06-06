# 0004. LLM-generated SQL with a read-only role + parser guard

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

The HR manager wants to ask questions about pay in plain English. The most flexible way to
answer arbitrary questions is to let an LLM translate the question into SQL and run it. That is
also the single most dangerous surface in the app: an LLM is an untrusted input source, and SQL it
emits could drop tables, exfiltrate other data, or run forever. We need the flexibility without
trusting the model.

The forces: power and flexibility (answer questions we didn't anticipate) versus safety (no writes,
no access beyond the salary tables, bounded cost and runtime), plus testability (CI must never call
a paid API).

## Decision

We will let the LLM generate **SQL only**, and defend in depth:

1. **Parser guard, not regex.** Generated SQL is parsed to an AST (sqlglot) and must be a single
   `SELECT`/`UNION` over a table whitelist (`employees`, `fx_rates`), using only an allowlist of
   functions (`avg, min, max, sum, count, round, coalesce, lower, upper`), with no DDL/DML, no
   multiple statements, no comments, and no system catalogs. Deny by default.

   > **Amended 2026-06-06 — CTEs + window functions allowed.** Real analytical questions ("which
   > department is overrepresented in the top 10% earners?") naturally need ranking/percentile SQL.
   > The allowlist now includes the read-only window functions (`row_number, rank, dense_rank,
   > ntile, percent_rank, cume_dist, lag, lead, first_value, last_value`, used with `OVER (...)`),
   > and CTE names (`WITH x AS (...)`) are resolved as local aliases rather than rejected as
   > unknown tables. **Security is unchanged in kind:** still single `SELECT`-only, read-only role,
   > row/time caps; a CTE body is still walked, so `WITH t AS (SELECT * FROM users)` is rejected on
   > the inner `users` reference (adversarial tests cover CTE-masking of `users`/`sqlite_master`).
   > The allowlist was also broadened in the same pass to the safe, deterministic SQLite built-ins
   > an analytics model actually uses (math/string/date/type plus `total`/`group_concat`); `CASE`/
   > `IIF` are control-flow, not callable functions, so they are skipped like operators. **Comments
   > are now stripped, not rejected:** the executed SQL is always the guard's own re-emitted AST
   > (`comments=False`), so a stray model comment is discarded; comment-based multi-statement
   > smuggling is still blocked by the single-statement parse and the `;` check (adversarial test
   > covers a `;` hidden in a comment).
   >
   > Two earlier bugs were also fixed alongside: sqlglot models boolean `AND`/`OR` as `Func`
   > subclasses (they were wrongly rejected — now operator nodes are skipped), and gemini-2.5-flash
   > truncated SQL under a 512-token output budget (raised so reasoning + SQL both fit).
2. **Read-only execution** with a hard 1000-row cap (and a statement timeout in production, where
   the query runs under a read-only database role with `SELECT`-only grants).
3. **No leakage.** Raw model output and internal errors are never returned; failures log internally
   with the request id and return a generic "couldn't answer — try rephrasing."
4. **Session cache** of `question → validated SQL` so a repeated question never re-prompts.
5. **Mocked in tests.** Unit/CI tests use a stub client; the real API is never called. Adversarial
   tests assert every attack class (DDL, DML, multi-statement, comments, system tables, bad
   functions) is rejected.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| LLM→SQL + parser guard + read-only role (chosen) | Flexible; defense in depth; testable offline | Guard must be maintained; some valid queries rejected | — |
| Regex/string filtering of SQL | Simple | Trivially bypassed (comments, casing, encodings); the charter forbids it | Not a real security boundary |
| LLM picks from a fixed set of canned queries | Very safe | Defeats the point — only answers anticipated questions | Too rigid for ad-hoc Q&A |
| LLM calls predefined tools/functions only | Safe and structured | Large surface to build for every metric; slower to ship | Good future direction; heavier than needed now |

## Consequences

Easier: the manager can ask open-ended questions; the guard makes "the model emitted something
dangerous" a non-event. Harder: the guard occasionally rejects a legitimate-but-unusual query (the
user rephrases), and the allowlists need updating if the schema grows. We accept reduced query
expressiveness (no joins to non-whitelisted tables, no exotic functions) as the price of safety. The
read-only role is a deployment responsibility documented for production.

## References

- `CLAUDE.md` §7 (LLM rules), §8 (rate limiting)
- Code: `app/llm/sql_guard.py`, `app/llm/prompt.py`, `app/llm/client.py`, `app/services/qa_service.py`
