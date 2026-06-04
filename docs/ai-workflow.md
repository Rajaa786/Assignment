# AI Workflow — how this was built with an AI collaborator

This project was built in an AI-native workflow (Claude Code). This document records *how*
AI was used, where it accelerated the work, and — more importantly — where human judgment
overrode it. The goal was leverage without abdication: AI writes a lot of the code; the
engineer owns every decision.

## The operating contract: `CLAUDE.md`

The single highest-leverage move was writing [`CLAUDE.md`](../CLAUDE.md) **first** — a detailed
engineering charter (stack, layering, SOLID rules, naming, testing, security, ADR policy) that the
agent must follow, with the explicit rule "if this file conflicts with a request, the file wins."
This turned vague "write good code" intent into enforceable constraints, so generated code arrived
already matching the house style instead of being corrected after the fact.

## How work was delegated

- **Plan before code.** Each feature started from the charter + a short plan, then proceeded in
  small, verifiable steps. Tests were written in the same step as the code and run before moving on.
- **Layer by layer, commit by commit.** The build follows the dependency direction
  (domain → core → models → repositories → services → api), one logical commit each, every commit
  green (`ruff` + `mypy --strict` + `pytest`). The git log reads as the story of the build.
- **Tight feedback loop.** After every change: lint, type-check, test. Failures were fixed
  immediately, not batched — e.g. the request-validation handler leaking a non-serializable
  `ValueError` was caught by an integration test and fixed before the commit.

## Sample prompts / instructions used

- "Build the `Money` value object: integer minor units + ISO 4217, exact `Decimal` arithmetic,
  currency mismatch raises, immutable. Add unit tests for rounding and currency safety."
- "Implement cursor (keyset) pagination per `CLAUDE.md` §5 — opaque base64 cursor, `limit+1`
  look-ahead, `{items, next_cursor, total}`. Write an ADR."
- "The NL Q&A SQL guard must be a parser, not a regex (charter §7). Use an AST. Reject DDL/DML,
  multi-statement, comments, system tables, non-allowlisted functions. Adversarial tests for each."
- "Run the full gate (ruff, mypy --strict, pytest) and fix anything before committing."

## Where human judgment overrode the AI

These are the decisions a reviewer should probe — none were taken blindly:

- **Scope reconciliation.** The plan and the charter diverged (the charter included an LLM Q&A
  feature and stricter money/pagination the first plan draft lacked). Rather than silently pick one,
  the trade-offs were surfaced and **decided explicitly** — keep the NL Q&A, keep integer minor
  units + cursor pagination — and the charter was edited to stay consistent (the `Compensation`
  aggregate was dropped as out of scope, documented as a deferred, additive change).
- **Tooling sanity.** An over-tight `mypy` flag (`disallow_any_explicit`) was flagging *library*
  base classes (pydantic `BaseSettings`), not our code. It was removed in favor of real `--strict`,
  with `Any` avoided by convention — the charter's intent without the false positives.
- **Dependencies are not added silently.** Adding `sqlglot` (for the parser-based SQL guard) was
  called out and justified against the charter's "ask before adding deps" rule, because a real
  security boundary warrants a real parser.
- **Honest reporting.** Where something couldn't be verified locally (Docker images — Docker isn't
  installed on the build machine) it is stated plainly rather than implied as done.

## What AI was *not* trusted to decide

Architecture and trade-offs (captured in [`docs/decisions/`](decisions/)), the data model, the
security posture of the Q&A feature, and what to deliberately leave out
([`requirements.md`](../requirements.md)). AI drafted; the ADRs record the reasoning a human stands
behind.
