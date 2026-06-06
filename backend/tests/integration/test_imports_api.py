"""Integration tests for CSV import and export endpoints."""

from __future__ import annotations

import csv
import io

from fastapi.testclient import TestClient

from tests.integration.test_employees_api import create_employee

HEADER = "first_name,last_name,email,department,job_title,level,employment_type,country,base_salary_amount,hire_date"  # noqa: E501


def csv_file(*rows: str) -> dict[str, tuple[str, bytes, str]]:
    content = ("\n".join([HEADER, *rows]) + "\n").encode("utf-8")
    return {"file": ("employees.csv", content, "text/csv")}


def test_import_persists_valid_rows(client: TestClient) -> None:
    files = csv_file(
        "Ada,Lovelace,ada@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01",
        "Alan,Turing,alan@acme.test,Engineering,Engineer,L5,Full-time,DE,150000.00,2020-02-02",
    )

    response = client.post("/api/v1/imports/employees", files=files)

    assert response.status_code == 200
    assert response.json()["inserted"] == 2
    assert client.get("/api/v1/employees").json()["total"] == 2


def test_dry_run_reports_without_persisting(client: TestClient) -> None:
    files = csv_file(
        "Ada,Lovelace,ada@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01"
    )

    response = client.post("/api/v1/imports/employees", files=files, params={"dry_run": True})

    assert response.json()["valid"] == 1
    assert response.json()["inserted"] == 0
    assert client.get("/api/v1/employees").json()["total"] == 0


def test_import_with_a_bad_row_persists_nothing(client: TestClient) -> None:
    files = csv_file(
        "Ada,Lovelace,ada@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01",
        "Bad,Row,nope,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01",
    )

    response = client.post("/api/v1/imports/employees", files=files)

    assert response.json()["inserted"] == 0
    assert response.json()["failed"] == 1
    assert client.get("/api/v1/employees").json()["total"] == 0


def test_export_streams_csv_of_current_employees(client: TestClient) -> None:
    create_employee(client, email="ada@acme.test", last_name="Lovelace", hire_date="2021-06-01")

    response = client.get("/api/v1/employees/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    header, *rows = list(csv.reader(io.StringIO(response.text)))
    assert header[0] == "employee_code"
    assert "hire_date" in header
    # Every data row must line up 1:1 with the header — no column drift.
    record = dict(zip(header, rows[0], strict=True))
    assert record["email"] == "ada@acme.test"
    assert record["hire_date"] == "2021-06-01"
