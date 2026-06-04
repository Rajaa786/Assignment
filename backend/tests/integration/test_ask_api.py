"""Integration tests for the natural-language Q&A endpoint with a stub LLM."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_llm_client, get_qa_cache
from app.main import app
from tests.integration.test_employees_api import create_employee


class SpyStubLlmClient:
    """Stub LLM that returns a fixed SQL string and counts how often it is called."""

    def __init__(self, sql: str) -> None:
        self._sql = sql
        self.calls = 0

    def generate_sql(self, system_prompt: str, question: str) -> str:
        self.calls += 1
        return self._sql


def use_stub(sql: str) -> SpyStubLlmClient:
    """Override the Q&A dependencies to use a stub LLM and a single fresh cache."""
    stub = SpyStubLlmClient(sql)
    cache: dict[str, str] = {}
    app.dependency_overrides[get_llm_client] = lambda: stub
    app.dependency_overrides[get_qa_cache] = lambda: cache
    return stub


@pytest.fixture(autouse=True)
def _clear_qa_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.pop(get_llm_client, None)
    app.dependency_overrides.pop(get_qa_cache, None)


def test_ask_runs_guarded_sql_and_returns_rows(client: TestClient) -> None:
    create_employee(client, email="a@acme.test", base_salary_amount="100000.00")
    use_stub("SELECT count(*) AS headcount FROM employees WHERE deleted_at IS NULL")

    response = client.post("/api/v1/ask", json={"question": "How many employees are there?"})

    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == [{"headcount": 1}]
    assert body["row_count"] == 1


def test_ask_rejects_dangerous_sql_without_touching_data(client: TestClient) -> None:
    create_employee(client, email="a@acme.test")
    use_stub("DROP TABLE employees")

    response = client.post("/api/v1/ask", json={"question": "delete everything"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "qa.unavailable"
    # data is intact
    assert client.get("/api/v1/employees").json()["total"] == 1


def test_repeated_question_is_cached_and_not_re_prompted(client: TestClient) -> None:
    create_employee(client, email="a@acme.test")
    stub = use_stub("SELECT count(*) AS n FROM employees WHERE deleted_at IS NULL")

    payload = {"question": "headcount please"}
    client.post("/api/v1/ask", json=payload)
    client.post("/api/v1/ask", json=payload)

    assert stub.calls == 1  # second call served from cache


def test_blank_question_is_rejected_by_validation(client: TestClient) -> None:
    response = client.post("/api/v1/ask", json={"question": "  "})

    assert response.status_code == 422
