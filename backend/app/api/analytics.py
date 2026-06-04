"""Analytics HTTP endpoints — the 'how do we pay people?' surface.

Each endpoint delegates to the analytics service and returns pre-aggregated figures
in USD. The dimension parameter is constrained to the three groupable attributes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_analytics_service
from app.schemas.analytics import (
    ByDimensionResponse,
    Dimension,
    DistributionResponse,
    PayEquityResponse,
    SummaryResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryResponse, summary="Payroll summary")
def summary(service: AnalyticsService = Depends(get_analytics_service)) -> SummaryResponse:
    """Return headcount, total payroll, and the mean and median salary (USD)."""
    return service.summary()


@router.get("/by-dimension", response_model=ByDimensionResponse, summary="Pay by dimension")
def by_dimension(
    dimension: Dimension = Query(default="department"),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ByDimensionResponse:
    """Return per-group pay statistics for a department, country, or level breakdown."""
    return service.by_dimension(dimension)


@router.get("/distribution", response_model=DistributionResponse, summary="Salary distribution")
def distribution(
    service: AnalyticsService = Depends(get_analytics_service),
) -> DistributionResponse:
    """Return the salary histogram across fixed USD bands."""
    return service.distribution()


@router.get("/pay-equity", response_model=PayEquityResponse, summary="Pay equity by group")
def pay_equity(
    dimension: Dimension = Query(default="department"),
    service: AnalyticsService = Depends(get_analytics_service),
) -> PayEquityResponse:
    """Return each group's median pay and its gap from the org-wide median."""
    return service.pay_equity(dimension)
