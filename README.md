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

## Run it (pick one)

### 1. Prebuilt images — fastest, no clone, no toolchain ⭐

Pulls published images from GHCR and starts the full stack, **auto-seeded with 10,000
employees** on first boot. The only file you need is `docker-compose.images.yml`.

```bash
curl -O https://raw.githubusercontent.com/OWNER/REPO/main/docker-compose.images.yml
docker compose -f docker-compose.images.yml up
# open http://localhost:8080     ·     API docs at http://localhost:8000/docs
```

_(Replace `OWNER/REPO` with this repository's path. Images: `ghcr.io/OWNER/acme-salary-api`
and `…-web`.)_

### 2. From source with Docker

```bash
docker compose up --build        # builds both images, auto-seeds 10k on first start
# web http://localhost:8080  ·  API http://localhost:8000
```

### 3. Local dev (hot reload)

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m app.seed.seed          # seed 10,000 employees (< 1s)
uvicorn app.main:app --reload    # http://localhost:8000  ·  docs at /docs

# Frontend (separate terminal)
cd web && pnpm install && pnpm dev   # http://localhost:5173
```

The natural-language Q&A works without an API key (it falls back to a safe stub query);
set an LLM key to use a real model — see Configuration.

## Configuration

All config is read from environment variables into one typed `Settings`
([backend/app/core/config.py](backend/app/core/config.py)) — 12-factor, no config in code.

**Natural-language Q&A is provider-pluggable** (`ADR-0012`). The provider is chosen by env and
falls back to a safe offline stub when no key is set, so the app always runs:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `auto` (default — pick whichever key is set), or force `anthropic` / `gemini` / `stub` |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) key |
| `GEMINI_API_KEY` | Google Gemini key |
| `LLM_MODEL` | optional model override (defaults: `claude-haiku-4-5`, `gemini-2.5-flash`) |

Have a Gemini key? `LLM_PROVIDER=gemini` + `GEMINI_API_KEY=…`. Adding another provider is one
builder in [backend/app/llm/factory.py](backend/app/llm/factory.py) — the selector never changes.

**Where secrets go per environment** (the LLM key is **backend-only** — never in the frontend):

- **Local / Docker Compose:** copy `.env.example` → `.env` at the repo root (gitignored) and set a
  key. Compose interpolates `${GEMINI_API_KEY}` etc. into the API container. Or pass inline:
  `GEMINI_API_KEY=… LLM_PROVIDER=gemini docker compose up`.
- **Fly.io (API):** `fly secrets set GEMINI_API_KEY=… LLM_PROVIDER=gemini` (encrypted, not in the image).
- **Vercel (web):** only `VITE_API_BASE` (the API origin). The frontend never holds an LLM key.

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
