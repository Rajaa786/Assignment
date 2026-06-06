"""Analytics: turning salary rows into the answers an HR manager asks.

All computation happens here in pure, testable steps over the projected salary rows
(``AnalyticsReader``). Money is reported in the base currency. Medians use the standard
definition (mean of the two middle values for an even count); aggregates are exact
because salaries are integer minor units.
"""

from __future__ import annotations

from decimal import Decimal

from app.core.logging import get_logger
from app.domain.currency import Currency
from app.repositories.analytics_repository import AnalyticsReader, SalaryRow
from app.schemas.analytics import (
    ByDimensionResponse,
    Dimension,
    DimensionStat,
    DistributionBucket,
    DistributionResponse,
    PayEquityGroup,
    PayEquityResponse,
    SummaryResponse,
)
from app.schemas.common import MoneyOut

logger = get_logger(__name__)

# Salary histogram bands in USD major units; the final band is open-ended.
_DISTRIBUTION_BOUNDS_USD = (0, 50_000, 100_000, 150_000, 200_000, 300_000)


def mean_minor(values: list[int]) -> int:
    """Return the integer mean of minor-unit values (0 for an empty list)."""
    return round(sum(values) / len(values)) if values else 0


def median_minor(values: list[int]) -> int:
    """Return the integer median of minor-unit values (0 for an empty list)."""
    if not values:
        return 0
    ordered = sorted(values)
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return round((ordered[middle - 1] + ordered[middle]) / 2)


class AnalyticsService:
    """Computes payroll summaries, per-dimension breakdowns, distributions, and equity."""

    def __init__(self, reader: AnalyticsReader, base_currency: Currency) -> None:
        self._reader = reader
        self._base_currency = base_currency

    def summary(self) -> SummaryResponse:
        """Return headcount, total payroll, and the mean and median salary (USD)."""
        salaries = [row.usd_minor for row in self._reader.active_salary_rows()]
        logger.info("analytics_summary_computed", headcount=len(salaries))
        return SummaryResponse(
            headcount=len(salaries),
            total_payroll_usd=self._money(sum(salaries)),
            average_salary_usd=self._money(mean_minor(salaries)),
            median_salary_usd=self._money(median_minor(salaries)),
        )

    def by_dimension(self, dimension: Dimension) -> ByDimensionResponse:
        """Return per-group pay statistics for a dimension, sorted by total spend."""
        grouped = self._group_salaries(dimension)
        stats = [
            DimensionStat(
                key=key,
                count=len(salaries),
                average_usd=self._money(mean_minor(salaries)),
                median_usd=self._money(median_minor(salaries)),
                min_usd=self._money(min(salaries)),
                max_usd=self._money(max(salaries)),
                total_usd=self._money(sum(salaries)),
            )
            for key, salaries in grouped.items()
        ]
        stats.sort(key=lambda stat: stat.total_usd.minor_units, reverse=True)
        logger.info("analytics_by_dimension_computed", dimension=dimension, groups=len(stats))
        return ByDimensionResponse(dimension=dimension, groups=stats)

    def distribution(self) -> DistributionResponse:
        """Return the salary histogram across fixed USD bands."""
        salaries = [row.usd_minor for row in self._reader.active_salary_rows()]
        factor = self._base_currency.minor_unit_factor
        buckets: list[DistributionBucket] = []
        for index, lower in enumerate(_DISTRIBUTION_BOUNDS_USD):
            is_last = index == len(_DISTRIBUTION_BOUNDS_USD) - 1
            upper = None if is_last else _DISTRIBUTION_BOUNDS_USD[index + 1]
            lower_minor = lower * factor
            upper_minor = None if upper is None else upper * factor
            count = sum(
                1
                for value in salaries
                if value >= lower_minor and (upper_minor is None or value < upper_minor)
            )
            buckets.append(DistributionBucket(lower_usd=lower, upper_usd=upper, count=count))
        logger.info("analytics_distribution_computed", buckets=len(buckets))
        return DistributionResponse(buckets=buckets)

    def pay_equity(self, dimension: Dimension) -> PayEquityResponse:
        """Return each group's median pay and its gap from the org-wide median."""
        rows = self._reader.active_salary_rows()
        overall_median = median_minor([row.usd_minor for row in rows])
        grouped = self._group_salaries(dimension)

        groups = [
            PayEquityGroup(
                key=key,
                count=len(salaries),
                median_usd=self._money(median_minor(salaries)),
                min_usd=self._money(min(salaries)),
                max_usd=self._money(max(salaries)),
                gap_vs_overall_pct=self._gap_percent(median_minor(salaries), overall_median),
            )
            for key, salaries in grouped.items()
        ]
        groups.sort(key=lambda group: group.median_usd.minor_units, reverse=True)
        logger.info("analytics_pay_equity_computed", dimension=dimension, groups=len(groups))
        return PayEquityResponse(
            dimension=dimension,
            overall_median_usd=self._money(overall_median),
            groups=groups,
        )

    def _group_salaries(self, dimension: Dimension) -> dict[str, list[int]]:
        """Bucket USD salaries by the given dimension attribute of each row."""
        grouped: dict[str, list[int]] = {}
        for row in self._reader.active_salary_rows():
            key = self._dimension_key(row, dimension)
            grouped.setdefault(key, []).append(row.usd_minor)
        return grouped

    @staticmethod
    def _dimension_key(row: SalaryRow, dimension: Dimension) -> str:
        if dimension == "department":
            return row.department
        if dimension == "country":
            return row.country
        return row.level

    @staticmethod
    def _gap_percent(group_median: int, overall_median: int) -> float:
        if overall_median == 0:
            return 0.0
        return round((group_median - overall_median) / overall_median * 100, 1)

    def _money(self, minor_units: int) -> MoneyOut:
        amount = Decimal(minor_units) / self._base_currency.minor_unit_factor
        return MoneyOut(amount=amount, currency=self._base_currency.code, minor_units=minor_units)
