"""Unit tests for LLM provider selection and the Gemini client wiring.

Selection is asserted by constructing Settings directly. The Gemini client is tested
with the google-genai SDK mocked, so no real API is ever called (CLAUDE.md §7).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.llm.client import AnthropicLlmClient, GeminiLlmClient, StubLlmClient
from app.llm.factory import build_llm_client


def settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {"anthropic_api_key": None, "gemini_api_key": None}
    base.update(overrides)
    return Settings(**base)


def test_auto_prefers_anthropic_when_its_key_is_set() -> None:
    client = build_llm_client(
        settings(llm_provider="auto", anthropic_api_key="a", gemini_api_key="g")
    )

    assert isinstance(client, AnthropicLlmClient)


def test_auto_uses_gemini_when_only_gemini_key_is_set() -> None:
    client = build_llm_client(settings(llm_provider="auto", gemini_api_key="g"))

    assert isinstance(client, GeminiLlmClient)


def test_auto_falls_back_to_stub_without_any_key() -> None:
    client = build_llm_client(settings(llm_provider="auto"))

    assert isinstance(client, StubLlmClient)


def test_explicit_gemini_builds_gemini_client() -> None:
    client = build_llm_client(settings(llm_provider="gemini", gemini_api_key="g"))

    assert isinstance(client, GeminiLlmClient)


def test_explicit_provider_without_its_key_falls_back_to_stub() -> None:
    client = build_llm_client(settings(llm_provider="anthropic"))

    assert isinstance(client, StubLlmClient)


def test_explicit_stub_is_always_the_stub() -> None:
    client = build_llm_client(settings(llm_provider="stub", anthropic_api_key="a"))

    assert isinstance(client, StubLlmClient)


def test_gemini_client_calls_the_sdk_and_returns_trimmed_text() -> None:
    fake_response = MagicMock(text="  SELECT 1  ")
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client) as constructor:
        client = GeminiLlmClient("secret-key", "gemini-2.5-flash")
        result = client.generate_sql("SYSTEM", "question")

    assert result == "SELECT 1"
    constructor.assert_called_once_with(api_key="secret-key")
    call = fake_client.models.generate_content.call_args
    assert call.kwargs["model"] == "gemini-2.5-flash"
    assert call.kwargs["contents"] == "question"
    assert call.kwargs["config"].system_instruction == "SYSTEM"
