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


class LlmClient(Protocol):
    """Produces a candidate SQL string for a question, given a system prompt."""

    def generate_sql(self, system_prompt: str, question: str) -> str:
        """Return candidate SQL for the question (unvalidated, untrusted)."""
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

    @staticmethod
    def _default(question: str) -> str:
        """A safe, generic query used when no specific responder is configured."""
        return (
            "SELECT department, count(*) AS headcount, "
            "round(avg(base_salary_usd_minor) / 100.0, 2) AS avg_salary_usd "
            "FROM employees WHERE deleted_at IS NULL GROUP BY department"
        )
