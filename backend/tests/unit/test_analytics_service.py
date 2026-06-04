"""Unit tests for analytics math and aggregation, on a small known dataset."""

from __future__ import annotations

import pytest

from app.domain.currency import Currency
from app.repositories.analytics_repository import SalaryRow
from app.services.analytics_service import AnalyticsService, mean_minor, median_minor

# Four employees, salaries already USD-normalized (minor units). Hand-computable.
ROWS = [
    SalaryRow(department="Engineering", country="US", level="L3", usd_minor=100_000_00),
    SalaryRow(department="Engineering", country="US", level="L5", usd_minor=200_000_00),
    SalaryRow(department="Sales", country="US", level="L3", usd_minor=60_000_00),
    SalaryRow(department="Sales", country="DE", level="L4", usd_minor=140_000_00),
]


class FakeAnalyticsReader:
    def __init__(self, rows: list[SalaryRow]) -> None:
        self._rows = rows

    def active_salary_rows(self) -> list[SalaryRow]:
        return list(self._rows)


def make_service(rows: list[SalaryRow]) -> AnalyticsService:
    return AnalyticsService(FakeAnalyticsReader(rows), Currency("USD"))


@pytest.mark.parametrize(
    ("values", "expected"),
    [([], 0), ([10], 10), ([10, 20, 30], 20), ([10, 20, 30, 40], 25)],
)
def test_median_minor(values: list[int], expected: int) -> None:
    assert median_minor(values) == expected


def test_mean_minor_rounds_to_nearest_integer() -> None:
    assert mean_minor([10, 11]) == 10  # 10.5 -> banker's rounding to even (10)
    assert mean_minor([]) == 0


def test_summary_reports_headcount_total_mean_median() -> None:
    summary = make_service(ROWS).summary()

    assert summary.headcount == 4
    assert summary.total_payroll_usd.minor_units == 500_000_00
    assert summary.average_salary_usd.minor_units == 125_000_00
    assert summary.median_salary_usd.minor_units == 120_000_00  # (100k + 140k) / 2


def test_by_dimension_groups_and_sorts_by_total() -> None:
    response = make_service(ROWS).by_dimension("department")

    assert response.groups[0].key == "Engineering"  # highest total
    assert response.groups[0].total_usd.minor_units == 300_000_00
    assert response.groups[0].median_usd.minor_units == 150_000_00
    assert response.groups[1].key == "Sales"
    assert response.groups[1].min_usd.minor_units == 60_000_00


def test_distribution_buckets_salaries_into_bands() -> None:
    response = make_service(ROWS).distribution()
    buckets = {(b.lower_usd, b.upper_usd): b.count for b in response.buckets}

    assert buckets[(50_000, 100_000)] == 1  # 60k
    assert buckets[(100_000, 150_000)] == 2  # 100k, 140k
    assert buckets[(200_000, 300_000)] == 1  # 200k
    assert sum(buckets.values()) == 4


def test_pay_equity_reports_gap_from_overall_median() -> None:
    response = make_service(ROWS).pay_equity("department")

    assert response.overall_median_usd.minor_units == 120_000_00
    engineering = next(group for group in response.groups if group.key == "Engineering")
    sales = next(group for group in response.groups if group.key == "Sales")
    assert engineering.gap_vs_overall_pct == 25.0  # 150k vs 120k
    assert sales.gap_vs_overall_pct == -16.7  # 100k vs 120k


def test_empty_dataset_is_safe() -> None:
    summary = make_service([]).summary()

    assert summary.headcount == 0
    assert summary.median_salary_usd.minor_units == 0
