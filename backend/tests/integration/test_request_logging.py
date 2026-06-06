"""Integration tests for the per-operation logging added across the APIs.

Each test wraps a request in ``capture_logs`` and asserts the expected structured
event fired with the right fields — the behavior, not the log wording. No salary
amounts are asserted because none are logged (CLAUDE.md §8).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from tests.integration.test_employees_api import create_employee
from tests.integration.test_imports_api import csv_file


def _events(logs: list[dict[str, object]]) -> set[object]:
    return {entry["event"] for entry in logs}


def test_employee_create_and_delete_emit_operation_events(client: TestClient) -> None:
    with capture_logs() as logs:
        body = create_employee(client)

    created = next(entry for entry in logs if entry["event"] == "employee_created")
    assert created["employee_id"] == body["id"]

    with capture_logs() as delete_logs:
        response = client.delete(f"/api/v1/employees/{body['id']}")

    assert response.status_code == 204
    assert "employee_deleted" in _events(delete_logs)


def test_analytics_summary_emits_event(client: TestClient) -> None:
    with capture_logs() as logs:
        client.get("/api/v1/analytics/summary")

    assert "analytics_summary_computed" in _events(logs)


def test_csv_import_completed_event_carries_counts(client: TestClient) -> None:
    files = csv_file(
        "Ada,Lovelace,ada@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01"
    )

    with capture_logs() as logs:
        client.post("/api/v1/imports/employees", files=files, params={"dry_run": True})

    completed = next(entry for entry in logs if entry["event"] == "csv_import_completed")
    assert completed["dry_run"] is True
    assert completed["valid"] == 1
    assert completed["inserted"] == 0


def test_not_found_logs_app_error(client: TestClient) -> None:
    with capture_logs() as logs:
        response = client.get("/api/v1/employees/999999")

    assert response.status_code == 404
    app_error = next(entry for entry in logs if entry["event"] == "app_error")
    assert app_error["code"] == "employee.not_found"
    assert app_error["status_code"] == 404


def test_invalid_body_logs_request_validation_failed(client: TestClient) -> None:
    with capture_logs() as logs:
        response = client.post("/api/v1/employees", json={})

    assert response.status_code == 422
    assert "request_validation_failed" in _events(logs)
