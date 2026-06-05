# 0012. Pluggable LLM provider (Strategy/factory) — Anthropic default, Gemini optional

- **Status**: Accepted
- **Date**: 2026-06-05
- **Deciders**: Raj Singh

## Context

The natural-language Q&A feature calls an LLM to draft SQL. The original charter locked this to the
Anthropic SDK, but an operator may have a key for a different provider (e.g. Google Gemini) and no
Anthropic key. Hard-wiring one vendor in the dependency wiring couples the app to a single API and a
single billing account, and makes "use the key I actually have" impossible without code edits.

The service already depends on an `LlmClient` **protocol**, not on Anthropic directly — so the only
real question is how the concrete client is chosen at runtime, and how that choice is configured.

## Decision

We will keep the `LlmClient` protocol as the seam and select the implementation with a small
**factory + registry** (`app/llm/factory.py`). Providers register a builder keyed by name
(`anthropic`, `gemini`); `build_llm_client(settings)` resolves the configured provider:

- `LLM_PROVIDER=auto` (default) → the first provider whose API key is set, else the offline stub.
- `LLM_PROVIDER=<name>` → that provider; a missing key **falls back to the stub** (logged) so the
  app never 500s on misconfiguration.
- `LLM_PROVIDER=stub` → always the offline stub.

Adding a provider is **registering one builder** — `build_llm_client` is never edited (Open/Closed).
Each provider supplies its own default model; `LLM_MODEL` optionally overrides it. Keys come from env
(`ANTHROPIC_API_KEY` / `GEMINI_API_KEY`), never code. Anthropic remains the default and recommended
provider; Gemini uses the `google-genai` SDK, lazy-imported so it only loads when used.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Protocol + factory/registry (chosen) | Strategy/OCP/DIP; config-driven; add a provider in one place; graceful stub fallback | A little indirection; one more dependency (google-genai) | — |
| Anthropic-only (original) | Simplest; one SDK | Can't use a Gemini-only key without code changes; vendor lock | The exact limitation we're removing |
| `if provider == "x"` chain in the dependency | No new file | Edits the selector for every new provider (not Open/Closed); grows messy | Violates OCP; the registry is barely more code and far cleaner |
| LiteLLM / a generic gateway dep | One client for many vendors | Heavy abstraction + dependency for two providers; less control over the prompt/SQL path | Over-engineered for the need |

## Consequences

Easier: run against whichever provider you have a key for by setting two env vars; tests stay offline
(stub); a third provider is a ~20-line builder. Harder: one more dependency (`google-genai`, in main
deps so the published image "just works" with a key), and two providers' model ids/quirks to keep in
mind. The SQL guard, read-only execution, row caps, and no-error-leakage rules are unchanged — they
sit *after* the client and protect every provider equally.

## References

- `CLAUDE.md` §7 (LLM rules, updated), §8 (secrets via env)
- Code: `app/llm/client.py` (`GeminiLlmClient`), `app/llm/factory.py`, `app/api/dependencies.py`
- Related: `ADR-0004` (SQL guard — provider-agnostic safety boundary)
