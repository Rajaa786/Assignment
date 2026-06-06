# Planning artifacts

These are the **actual plan-mode documents** produced while building the recent feature
work on this repo, with an AI pair (Claude Code). They are included verbatim — context,
chosen approach, alternatives weighed, and the verification steps used — so a reviewer can
see *how* the work was reasoned about, not just the final diff.

They complement [`../ai-workflow.md`](../ai-workflow.md) (how this was built with an AI
collaborator) and the [`../decisions/`](../decisions/) ADRs (the durable decisions). A plan
is the working draft; the ADR is the decision that survived; the commit is the result.

| # | Plan | Produced | Lands in |
|---|---|---|---|
| 0001 | [Pluggable LLM provider + config/secret management](0001-pluggable-llm-provider.md) | provider behind one protocol, env-selected, Docker/compose secret wiring | `ADR-0012`; `app/llm/factory.py` |
| 0002 | [Request-flow logging across the non-QA APIs](0002-request-flow-logging.md) | operation/flow events on employees, analytics, CSV import/export | `ADR-0014` |
| 0003 | [INFO-tier per-step LLM logging + overridable `LOG_FORMAT`](0003-info-tier-llm-logging.md) | prompt/model-output/executed-SQL at INFO; console default | `ADR-0013` (amended) |
| 0004 | [Phase 2 — live deploy (Fly.io API + Vercel web)](0004-phase-2-deployment.md) | API on Fly (`bom`, scale-to-zero), web on Vercel, CORS wired; includes an as-built outcome | `ADR-0002`/`0011`; live URLs in README |

> These are working drafts captured during the build, lightly trimmed only to remove
> cross-session scaffolding. Where a plan and the shipped code differ, the **code and its
> ADR are authoritative** — a plan reflects intent at the time it was written.
