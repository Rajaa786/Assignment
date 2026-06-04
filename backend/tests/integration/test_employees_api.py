"""Integration tests for the employee endpoints against in-memory SQLite."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def make_payload(**overrides: Any) -> dict[str, Any]:
    """Return a valid create payload, overridable per test."""
    payload: dict[str, Any] = {
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace@acme.test",
        "department": "Engineering",
        "job_title": "Engineer",
        "level": "L4",
        "employment_type": "Full-time",
        "country": "US",
        "base_salary_amount": "150000.00",
        "hire_date": "2021-06-01",
    }
    payload.update(overrides)
    return payload


def create_employee(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post("/api/v1/employees", json=make_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_create_derives_code_currency_and_usd_salary(client: TestClient) -> None:
    body = create_employee(client)

    assert body["employee_code"].startswith("EMP-")
    assert body["base_salary"]["currency"] == "USD"
    assert body["base_salary"]["minor_units"] == 150_000_00
    assert body["base_salary_usd"]["currency"] == "USD"
    assert body["base_salary_usd"]["minor_units"] == 150_000_00


def test_create_normalizes_non_usd_salary_to_usd(client: TestClient) -> None:
    body = create_employee(client, country="DE", base_salary_amount="100000.00")

    assert body["base_salary"]["currency"] == "EUR"
    # 100,000 EUR * 1.08 = 108,000 USD
    assert body["base_salary_usd"]["minor_units"] == 108_000_00


def test_create_duplicate_email_returns_conflict(client: TestClient) -> None:
    create_employee(client, email="dup@acme.test")

    response = client.post("/api/v1/employees", json=make_payload(email="dup@acme.test"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "resource.conflict"


def test_create_invalid_email_returns_validation_error(client: TestClient) -> None:
    response = client.post("/api/v1/employees", json=make_payload(email="not-an-email"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request.invalid"


def test_create_unsupported_country_returns_validation_error(client: TestClient) -> None:
    response = client.post("/api/v1/employees", json=make_payload(country="XX"))

    assert response.status_code == 422


def test_get_unknown_employee_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/employees/123456")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "employee.not_found"


def test_patch_recomputes_usd_salary(client: TestClient) -> None:
    created = create_employee(client, country="DE", base_salary_amount="100000.00")

    response = client.patch(
        f"/api/v1/employees/{created['id']}", json={"base_salary_amount": "200000.00"}
    )

    assert response.status_code == 200
    # 200,000 EUR * 1.08 = 216,000 USD
    assert response.json()["base_salary_usd"]["minor_units"] == 216_000_00


def test_delete_soft_deletes_employee(client: TestClient) -> None:
    created = create_employee(client)

    delete_response = client.delete(f"/api/v1/employees/{created['id']}")
    assert delete_response.status_code == 204

    assert client.get(f"/api/v1/employees/{created['id']}").status_code == 404
    listing = client.get("/api/v1/employees").json()
    assert listing["total"] == 0


def test_list_pagination_walks_every_row_once(client: TestClient) -> None:
    for index in range(5):
        create_employee(client, email=f"person{index}@acme.test", last_name=f"Last{index}")

    seen_ids: list[int] = []
    cursor: str | None = None
    pages = 0
    while True:
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        body = client.get("/api/v1/employees", params=params).json()
        seen_ids.extend(item["id"] for item in body["items"])
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert body["total"] == 5
    assert sorted(seen_ids) == seen_ids  # ascending by id
    assert len(set(seen_ids)) == 5
    assert pages == 3  # 2 + 2 + 1


def test_list_filters_by_country(client: TestClient) -> None:
    create_employee(client, email="us@acme.test", country="US")
    create_employee(client, email="de@acme.test", country="DE", base_salary_amount="90000.00")

    body = client.get("/api/v1/employees", params={"country": "DE"}).json()

    assert body["total"] == 1
    assert body["items"][0]["country"] == "DE"


def test_list_sorts_by_salary_descending(client: TestClient) -> None:
    create_employee(client, email="low@acme.test", base_salary_amount="80000.00")
    create_employee(client, email="high@acme.test", base_salary_amount="250000.00")

    body = client.get("/api/v1/employees", params={"sort_by": "salary", "sort_dir": "desc"}).json()

    salaries = [item["base_salary_usd"]["minor_units"] for item in body["items"]]
    assert salaries == sorted(salaries, reverse=True)


def test_malformed_cursor_returns_invalid_cursor_error(client: TestClient) -> None:
    response = client.get("/api/v1/employees", params={"cursor": "garbage!!"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "pagination.invalid_cursor"
