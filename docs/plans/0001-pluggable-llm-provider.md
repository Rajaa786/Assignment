# Plan — Pluggable LLM provider (Anthropic + Gemini) + config/secret management

## Context

The Q&A feature is hard-wired to Anthropic in the dependency wiring, and there is **no way to
supply the LLM key through Docker/compose** today. The user may have a **Gemini** key instead. Goal:
make the LLM provider swappable with clean design, and make configuration/secrets flow correctly
through every environment (local, compose, published images, Fly, Vercel).

The good news: the seam already exists. `app/llm/client.py` defines an `LlmClient` **Protocol** that
the service depends on (Dependency Inversion). Adding Gemini is a new implementation behind that
protocol plus a small selection factory — **Strategy + Open/Closed**: new providers are added without
editing existing ones or the selector.

## Design

```
LlmClient (Protocol)            # app/llm/client.py  (unchanged seam)
 ├─ AnthropicLlmClient          # existing
 ├─ GeminiLlmClient             # NEW (lazy-imports google-genai)
 └─ StubLlmClient               # existing (offline default / tests)

build_llm_client(settings) -> LlmClient   # app/llm/factory.py  (NEW)
   registry { "anthropic": _build_anthropic, "gemini": _build_gemini }
   LLM_PROVIDER = auto | anthropic | gemini | stub
     auto      -> first provider whose key is set, else stub
     <name>    -> that provider; if its key is missing -> warn + stub (never 500)
```
Adding a provider later = add one builder to the registry. `build_llm_client` itself never changes.

## Changes

### LLM provider code
- `app/llm/client.py` — add `GeminiLlmClient` (lazy `from google import genai`; default model
  `gemini-2.5-flash`); add `DEFAULT_ANTHROPIC_MODEL` / `DEFAULT_GEMINI_MODEL` constants.
- `app/llm/factory.py` (NEW) — the registry + `build_llm_client(settings)` selection (above).
- `app/api/dependencies.py` — `get_llm_client()` becomes `return build_llm_client(settings)`.

### Config (12-factor: everything via env, one `Settings`)
- `app/core/config.py` — add `llm_provider: Literal["auto","anthropic","gemini","stub"] = "auto"`
  and `gemini_api_key: str | None = None`; change `llm_model` to `str | None = None` (optional
  override; each provider supplies its own default so a Gemini run never uses an Anthropic model id).
- `pyproject.toml` — add `google-genai` to dependencies; add `google.*` to the mypy ignore-missing list.
- `backend/.env.example` — document `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, optional `LLM_MODEL`.

### Secret/config plumbing across environments
- `docker-compose.yml` and `docker-compose.images.yml` — pass the LLM config into the api service via
  interpolation so nothing secret is committed:
  `LLM_PROVIDER: ${LLM_PROVIDER:-auto}`, `ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}`,
  `GEMINI_API_KEY: ${GEMINI_API_KEY:-}`. Compose auto-reads a gitignored root `.env` for these.
- `.env.example` (repo root, NEW) — the compose interpolation file (keys blank); real `.env` is
  gitignored.
- The rule (documented): **the LLM key is backend-only** — it goes in `.env`/compose/`fly secrets`,
  **never** in the frontend/Vercel build (Vercel only gets `VITE_API_BASE`). Empty keys ⇒ stub, so
  the app always runs.

### Docs / decisions
- `README.md` — short **Configuration** section: where each setting lives per environment
  (local `.env` → compose `${VAR}` interpolation → `fly secrets set` → Vercel env), and how
  `LLM_PROVIDER` / the two keys select a provider.
- `docs/decisions/0012-pluggable-llm-provider.md` (NEW ADR) + CLAUDE.md ADR table row.
- `CLAUDE.md` §7 — reconcile: "Anthropic is the **default** provider; LLM access is behind the
  `LlmClient` protocol with a provider factory (Anthropic, Gemini, Stub) chosen by config." Guard,
  read-only execution, mock-in-tests rules all unchanged.

### Tests
- `tests/unit/test_llm_factory.py` (NEW) — construct `Settings(...)` with kwargs and assert selection:
  auto→anthropic when anthropic key set; auto→gemini when only gemini key; auto→stub when none;
  explicit `gemini`→GeminiLlmClient; explicit `anthropic` with no key→stub fallback; `stub`→stub.
- One `GeminiLlmClient.generate_sql` test with the `google.genai` client **mocked** (no network):
  asserts it passes `system_instruction` and returns the text. Real API is never called (CLAUDE.md §7).

## Verification
- `cd backend && ruff check && mypy app && pytest` — green incl. new factory tests.
- `docker compose config` and `docker compose -f docker-compose.images.yml config` show the
  `LLM_PROVIDER`/`*_API_KEY` env wired into the api service.
- Container sanity (no real key): `LLM_PROVIDER=stub docker compose up` → `/ask` returns rows
  (stub); with no keys, logs show stub selection. (No real Gemini/Anthropic call — charter rule.)

## User actions (per environment, documented in README)
- Local/compose: put `GEMINI_API_KEY=...` (or `ANTHROPIC_API_KEY=...`) in a gitignored root `.env`.
- Fly: `fly secrets set GEMINI_API_KEY=... LLM_PROVIDER=gemini`.
- Vercel: nothing LLM-related (frontend never holds the key).
