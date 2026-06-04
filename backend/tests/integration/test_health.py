"""Integration tests for the liveness and readiness probes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_reports_ok(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_ready_when_database_reachable(client: TestClient) -> None:
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_every_response_carries_a_request_id_header(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.headers["X-Request-ID"]


def test_request_id_is_echoed_from_the_inbound_header(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "fixed-id-123"})

    assert response.headers["X-Request-ID"] == "fixed-id-123"
