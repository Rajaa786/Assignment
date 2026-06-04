"""Transport schemas for the analytics endpoints.

Every monetary figure is reported in the base currency (USD) as :class:`MoneyOut`,
because comparing pay across countries only makes sense once normalized. The endpoints
return pre-aggregated buckets and per-group statistics — never raw employee rows.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import MoneyOut

Dimension = Literal["department", "country", "level"]


class SummaryResponse(BaseModel):
    """Headline numbers answering 'how much, and how typically, do we pay?'"""

    headcount: int = Field(description="Number of active employees.")
    total_payroll_usd: MoneyOut = Field(description="Sum of all base salaries, USD-normalized.")
    average_salary_usd: MoneyOut = Field(description="Mean base salary, USD-normalized.")
    median_salary_usd: MoneyOut = Field(description="Median base salary, USD-normalized.")


class DimensionStat(BaseModel):
    """Aggregated pay statistics for one group (one department, country, or level)."""

    key: str = Field(description="The group value, e.g. 'Engineering' or 'US'.")
    count: int
    average_usd: MoneyOut
    median_usd: MoneyOut
    min_usd: MoneyOut
    max_usd: MoneyOut
    total_usd: MoneyOut


class ByDimensionResponse(BaseModel):
    """Per-group pay statistics for a chosen dimension, sorted by total spend."""

    dimension: Dimension
    groups: list[DimensionStat]


class DistributionBucket(BaseModel):
    """A salary band and how many employees fall in it (USD major units)."""

    lower_usd: int = Field(description="Inclusive lower bound of the band, in USD.")
    upper_usd: int | None = Field(description="Exclusive upper bound, or null for the top band.")
    count: int


class DistributionResponse(BaseModel):
    """The salary histogram: fixed USD bands with employee counts."""

    buckets: list[DistributionBucket]


class PayEquityGroup(BaseModel):
    """One group's pay position relative to the organization-wide median."""

    key: str
    count: int
    median_usd: MoneyOut
    min_usd: MoneyOut
    max_usd: MoneyOut
    gap_vs_overall_pct: float = Field(
        description="Percent the group's median sits above (+) or below (-) the overall median."
    )


class PayEquityResponse(BaseModel):
    """Median pay by group versus the overall median — a first read on pay equity."""

    dimension: Dimension
    overall_median_usd: MoneyOut
    groups: list[PayEquityGroup]
