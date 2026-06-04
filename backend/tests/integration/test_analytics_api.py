"""Integration tests for the analytics endpoints with seeded employees."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.integration.test_employees_api import create_employee


def seed_three_us_employees(client: TestClient) -> None:
    """Create three US employees (salary == USD) with known salaries."""
    for index, salary in enumerate((100000, 200000, 60000)):
        create_employee(
            client,
            email=f"a{index}@acme.test",
            last_name=f"Person{index}",
            base_salary_amount=f"{salary}.00",
        )


def test_summary_reflects_created_employees(client: TestClient) -> None:
    seed_three_us_employees(client)

    body: dict[str, Any] = client.get("/api/v1/analytics/summary").json()

    assert body["headcount"] == 3
    assert body["total_payroll_usd"]["minor_units"] == 360_000_00
    assert body["median_salary_usd"]["minor_units"] == 100_000_00


def test_by_dimension_country_groups_results(client: TestClient) -> None:
    create_employee(client, email="us@acme.test", country="US", base_salary_amount="120000.00")
    create_employee(client, email="de@acme.test", country="DE", base_salary_amount="100000.00")

    body = client.get("/api/v1/analytics/by-dimension", params={"dimension": "country"}).json()

    assert body["dimension"] == "country"
    keys = {group["key"] for group in body["groups"]}
    assert keys == {"US", "DE"}


def test_pay_equity_returns_overall_median_and_groups(client: TestClient) -> None:
    seed_three_us_employees(client)

    body = client.get("/api/v1/analytics/pay-equity", params={"dimension": "department"}).json()

    assert body["overall_median_usd"]["minor_units"] == 100_000_00
    assert body["groups"][0]["key"] == "Engineering"


def test_invalid_dimension_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/analytics/by-dimension", params={"dimension": "salary"})

    assert response.status_code == 422
