# 0013. Request-scoped structured tracing for the Q&A path

- **Status**: Accepted
- **Date**: 2026-06-06
- **Deciders**: Raj Singh

## Context

`POST /api/v1/ask` is the highest-risk surface in the app: it prompts an LLM, validates
the generated SQL through the guard, and executes it read-only. When something looks
wrong, the operator needs to see what happened — which provider answered, what SQL was
produced, whether the guard rejected it, how many rows came back, and the exact error on
failure. As built, the service logged **only** in its three failure branches, and even
those logged `error=str(exc)` with no stack trace. A successful `/ask` produced no
app-level log at all; the only line in `docker logs` was uvicorn's access log
(`POST /api/v1/ask 200 OK`). With `LLM_PROVIDER=auto` and no key, the app silently falls
back to the offline stub — indistinguishable from a real provider in the logs.

The logging infrastructure was already adequate: structlog → stdout, a `request_id`
bound by middleware and echoed as `X-Request-ID`. What was missing was *using* it to
trace the request, plus a rule for what is safe to log given `CLAUDE.md` §8 ("logs never
contain salary amounts"). A model-generated `WHERE base_salary_usd_minor > N` could echo
an amount, so raw SQL can't go to the default log level unconditionally.

## Decision

We will emit an ordered, `request_id`-correlated **structured trace** across the Q&A
stages — `qa_request_received` → `qa_sql_generated` (or `qa_cache_hit`) → `qa_executed`
→ `qa_answered`, with `qa_llm_error` / `qa_sql_rejected` / `qa_execution_error` on the
failure paths. Each event carries the provider label, per-stage latency (`*_ms`), and
counts. Error events include `error_type` and `exc_info` (full stack trace, rendered into
the JSON `exception` field via `format_exc_info`).

Logging is **tiered for PII** (the core of this decision):

- **INFO**: the manager's question (capped), question/SQL **hashes** (`*_sha8`),
  `sql_chars`, `row_count`, `truncated`, latencies, provider/model. No DB values, no raw
  SQL.
- **DEBUG** (`LOG_LEVEL=debug`): the raw candidate SQL (`qa_sql_candidate`). The
  "show me exactly what the model produced" switch; off in production.

> **Amended 2026-06-06 — raw I/O promoted to INFO.** The DEBUG tier above proved
> impractical for the actual operator (one HR manager debugging their own queries from
> `docker logs`, which run at INFO). We now log the **model input** (`qa_prompt_built`:
> system prompt + question), the **model output** (`qa_sql_candidate`: raw pre-guard SQL),
> and the **executed SQL** (`sql` field on `qa_sql_generated` / `qa_executed` / `qa_cache_hit`)
> all at **INFO**. This is a deliberate, accepted exception to §8: a generated `WHERE` may
> echo a salary threshold the manager typed. It is bounded — result **rows** (actual
> compensation) are still never logged — and acceptable for a single-persona internal tool
> with no public surface (`ADR-0009`). The "Log everything at INFO" row below was rejected
> for a *public* service; this app is not one. To quiet it, lower the level or flip
> `LOG_FORMAT`/`LOG_LEVEL` (now overridable in compose) — the trace structure is unchanged.

Provider/model is surfaced through a new `describe()` method on the `LlmClient` protocol
(`anthropic:<model>`, `gemini:<model>`, `stub`) so the service never reaches into a
client's private fields. The generic user-facing message is unchanged (§7).

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Tiered structured trace + `describe()` (chosen) | Full request story; PII-safe by default; raw SQL on demand; provider visible; no new deps | A handful of log calls in the service; one protocol method added to 3 impls | — |
| Status quo (errors-only, rely on uvicorn access log) | No work | Happy path invisible; stub vs real provider indistinguishable; no stack traces | The exact problem being fixed |
| Log everything (incl. raw SQL) at INFO | Maximum detail with no flag | A generated `WHERE` clause can leak a salary amount into prod logs | Violates §8 |
| OpenTelemetry spans + a tracing backend | Industry-standard distributed tracing; flame graphs | Heavy dependency + collector for a single-process synchronous app | Over-engineered (§18); structlog + `request_id` already correlates |

## Consequences

Easier: one `/ask` is followed end to end by `request_id`; an operator sees the provider,
timings, and (at DEBUG) the exact SQL; failures carry a typed, stack-traced reason while
the HTTP response stays generic. We also fixed a latent gap — `format_exc_info` was absent,
so `exc_info` would not have serialized under JSON output in the container.

Harder / given up: the `LlmClient` protocol grew a second method (additive, LSP-safe —
every fake must now implement `describe()`); there is no distributed-tracing backend, so
cross-service correlation beyond `request_id` is out. Uvicorn's access log stays separate
(plain text, no `request_id`) — unifying it is deferred as not worth the log-config
override for one HR user.

## References

- `CLAUDE.md` §7 (no raw error leakage), §8 (no salary amounts in logs), §14 (stack trace
  + request id), §18 (no premature distribution)
- Code: `app/services/qa_service.py`, `app/llm/client.py` (`describe()`),
  `app/llm/factory.py`, `app/core/logging.py` (`format_exc_info`)
- Related: `ADR-0004` (SQL guard), `ADR-0012` (pluggable provider)
