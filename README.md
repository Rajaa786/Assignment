# ACME Salary Management

Web software that replaces the HR team's salary spreadsheets for a 10,000-employee,
multi-country organization. An HR manager can **manage salary records** and **answer
questions about how the org pays people** — through a fast analytics dashboard and a
natural-language Q&A box backed by guarded, read-only SQL.

> Built for the Incubyte take-home assessment. The engineering contract this repo is
> held to lives in [`CLAUDE.md`](CLAUDE.md); the product scope and deliberate cuts live
> in [`requirements.md`](requirements.md); architecture and trade-offs live in
> [`docs/architecture.md`](docs/architecture.md) and [`docs/decisions/`](docs/decisions/).

---

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Alembic |
| Database | SQLite (local) → PostgreSQL / Neon (prod), one engine factory chosen by `DATABASE_URL` |
| NL Q&A | Anthropic Claude → read-only SQL behind a parser guard |
| Frontend | Vite · React 18 · TypeScript · shadcn/ui · TanStack Query/Table · Recharts |
| Tests | pytest · factory-boy (API) · Vitest · React Testing Library (web) |
| Deploy | Docker Compose (local parity) · Fly.io (API) · Vercel (web) |

## Quick start

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head            # apply migrations
python -m app.seed.seed          # seed 10,000 employees (< 10s)
uvicorn app.main:app --reload    # http://localhost:8000  ·  docs at /docs

# Frontend
cd web
pnpm install
pnpm dev                         # http://localhost:5173
```

Or run the whole stack with one command (web on :8080, API on :8000):

```bash
docker compose up
docker compose exec api python -m app.seed.seed   # seed 10k employees (once)
```

The natural-language Q&A works without an API key (it falls back to a safe stub query);
set `ANTHROPIC_API_KEY` in `.env` to use the real model.

## Tests

```bash
cd backend && pytest          # fast, deterministic, no network (97 tests)
cd web && pnpm test           # Vitest + React Testing Library
```

## Project layout

```
backend/app/
  api/          FastAPI routers — HTTP concerns only
  services/     business logic & orchestration
  repositories/ data access (SQLAlchemy queries)
  models/       SQLAlchemy ORM models
  schemas/      Pydantic transport schemas
  domain/       pure value objects: Money, Currency, Country, EmployeeId
  core/         config, db, logging, errors, pagination, rate-limit
  llm/          NL Q&A: prompt building, SQL guard, client
  seed/         reference data + the 10k generator
web/            Vite + React frontend (pages, api hooks, ui primitives)
docs/           architecture diagram, ADRs, AI workflow, performance notes
```

## Documentation

- [`requirements.md`](requirements.md) — scope and what we deliberately left out (with reasoning)
- [`docs/architecture.md`](docs/architecture.md) — diagram, data model, request flows, trade-offs
- [`docs/decisions/`](docs/decisions/) — 10 ADRs (FastAPI, money model, cursor pagination, SQL guard, …)
- [`docs/ai-workflow.md`](docs/ai-workflow.md) — how this was built with an AI collaborator, and where judgment overrode it
- [`docs/performance.md`](docs/performance.md) — performance considerations
- `CLAUDE.md` — the engineering charter the codebase is held to

## Live demo & video

- **App:** _deploy step — link added in README on deploy_
- **Demo video:** _link added after recording_
