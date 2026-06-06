"""LLM client abstraction for turning a question into candidate SQL.

Services depend on the :class:`LlmClient` protocol, not on Anthropic directly, so the
real client is swapped for a deterministic mock in tests and local dev (the real API is
never called in unit tests or CI; ``CLAUDE.md`` §7). The client only *produces* candidate
SQL — validating and executing it is the service's and guard's job.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)

# Each provider's default model, used when no explicit LLM_MODEL override is set.
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class LlmClient(Protocol):
    """Produces a candidate SQL string for a question, given a system prompt."""

    def generate_sql(self, system_prompt: str, question: str) -> str:
        """Return candidate SQL for the question (unvalidated, untrusted)."""
        ...

    def describe(self) -> str:
        """Return a short ``provider:model`` label for logs (carries no secret)."""
        ...


class AnthropicLlmClient:
    """LlmClient backed by the Anthropic Messages API.

    Lazily constructs the SDK client so importing this module never requires the
    ``anthropic`` package to be configured (tests use the mock instead).
    """

    def __init__(self, api_key: str, model: str, max_tokens: int = 512) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens

    def generate_sql(self, system_prompt: str, question: str) -> str:
        """Call the model and return its raw text completion (candidate SQL)."""
        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": question}],
        )
        parts = [block.text for block in message.content if block.type == "text"]
        return "".join(parts).strip()

    def describe(self) -> str:
        """Return an ``anthropic:<model>`` label for structured logs."""
        return f"anthropic:{self._model}"


class GeminiLlmClient:
    """LlmClient backed by Google's Gemini API (google-genai SDK).

    Same contract as :class:`AnthropicLlmClient` — produce candidate SQL from a system
    prompt and a question. The SDK is imported lazily so the module loads without the
    package configured, and the schema/rules go in as the system instruction.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens

    def generate_sql(self, system_prompt: str, question: str) -> str:
        """Call Gemini and return its raw text completion (candidate SQL)."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self._model,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                # gemini-2.5-flash "thinks" by default and reasoning tokens share this
                # budget; 512 left nothing for the SQL on hard questions, truncating it
                # mid-statement. Keep thinking on (it helps multi-step analytical SQL) and
                # give it ample room so both the reasoning and the final SQL fit.
                max_output_tokens=self._max_tokens,
                temperature=0,
            ),
        )
        return (response.text or "").strip()

    def describe(self) -> str:
        """Return a ``gemini:<model>`` label for structured logs."""
        return f"gemini:{self._model}"


class StubLlmClient:
    """Deterministic LlmClient for local dev and tests.

    Maps questions to SQL via a supplied function (default: a single safe query).
    Never touches the network, so unit tests and CI are fast and offline.
    """

    def __init__(self, responder: Callable[[str], str] | None = None) -> None:
        self._responder = responder or self._default

    def generate_sql(self, system_prompt: str, question: str) -> str:
        """Return canned SQL for the question."""
        return self._responder(question)

    def describe(self) -> str:
        """Return the ``stub`` label so logs show the offline client is active."""
        return "stub"

    @staticmethod
    def _default(question: str) -> str:
        """A safe, generic query used when no specific responder is configured."""
        return (
            "SELECT department, count(*) AS headcount, "
            "round(avg(base_salary_usd_minor) / 100.0, 2) AS avg_salary_usd "
            "FROM employees WHERE deleted_at IS NULL GROUP BY department"
        )
