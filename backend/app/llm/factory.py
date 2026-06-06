"""Select and build the LLM client for the configured provider.

This is the one place that knows which concrete :class:`LlmClient` to use. Providers
live in a registry, so a new provider is added by registering one builder — never by
editing :func:`build_llm_client` (Open/Closed). Selection:

- ``LLM_PROVIDER=auto``  → the first provider whose API key is set, else the stub.
- ``LLM_PROVIDER=<name>`` → that provider; a missing key falls back to the stub
  (with a warning) so the app never 500s on misconfiguration.
- ``LLM_PROVIDER=stub``  → always the offline stub.
"""

from __future__ import annotations

from collections.abc import Callable

from app.core.config import Settings
from app.core.logging import get_logger
from app.llm.client import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_GEMINI_MODEL,
    AnthropicLlmClient,
    GeminiLlmClient,
    LlmClient,
    StubLlmClient,
)

logger = get_logger(__name__)


def _build_anthropic(settings: Settings) -> LlmClient | None:
    if not settings.anthropic_api_key:
        return None
    return AnthropicLlmClient(
        settings.anthropic_api_key, settings.llm_model or DEFAULT_ANTHROPIC_MODEL
    )


def _build_gemini(settings: Settings) -> LlmClient | None:
    if not settings.gemini_api_key:
        return None
    return GeminiLlmClient(settings.gemini_api_key, settings.llm_model or DEFAULT_GEMINI_MODEL)


# Provider name -> builder. A builder returns None when its key is absent. Register a
# new provider here (and add its key to Settings); the selection logic is untouched.
_BUILDERS: dict[str, Callable[[Settings], LlmClient | None]] = {
    "anthropic": _build_anthropic,
    "gemini": _build_gemini,
}

# Order tried when LLM_PROVIDER=auto.
_AUTO_ORDER = ("anthropic", "gemini")


def build_llm_client(settings: Settings) -> LlmClient:
    """Return the LLM client for the configured provider (never raises on missing keys)."""
    provider = settings.llm_provider

    # The happy-path selection is logged at DEBUG: the client is built per request, so
    # an INFO line here would repeat on every /ask. Per-request provider visibility lives
    # in the `qa_request_received` event. Misconfiguration (no/absent key) stays louder.
    if provider == "stub":
        logger.debug("llm_provider_selected", provider="stub")
        return StubLlmClient()

    if provider == "auto":
        for name in _AUTO_ORDER:
            client = _BUILDERS[name](settings)
            if client is not None:
                logger.debug("llm_provider_selected", provider=name)
                return client
        logger.info("llm_no_api_key_configured_using_stub")
        return StubLlmClient()

    client = _BUILDERS[provider](settings)
    if client is None:
        logger.warning("llm_provider_missing_key_using_stub", provider=provider)
        return StubLlmClient()
    logger.debug("llm_provider_selected", provider=provider)
    return client
