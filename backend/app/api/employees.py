"""Employee HTTP endpoints — REST over the employee service.

Thin by design: parse and validate input, delegate to the service, return a response
schema. No business rules, no ORM, no transactions here. List uses cursor pagination
(``ADR-0007``); salary filters are accepted in USD major units and converted to the
minor units the data layer compares against.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_csv_service, get_employee_service
from app.core.pagination import SortDirection
from app.domain.currency import Currency
from app.domain.enums import Department, Level
from app.repositories.employee_repository import EmployeeFilters
from app.schemas.common import Page
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services.csv_service import EmployeeCsvService
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])

SortField = Annotated[str, Query(pattern="^(id|name|salary|hire_date)$")]
_USD = Currency("USD")


def _to_usd_minor(amount: Decimal | None) -> int | None:
    """Convert an optional USD major-unit amount to integer minor units (cents)."""
    return None if amount is None else int(amount * _USD.minor_unit_factor)


def _build_filters(
    q: str | None,
    department: Department | None,
    country: str | None,
    level: Level | None,
    salary_usd_min: Decimal | None,
    salary_usd_max: Decimal | None,
) -> EmployeeFilters:
    """Assemble the repository filter object from raw query parameters."""
    return EmployeeFilters(
        search=q,
        department=department.value if department else None,
        country=country.upper() if country else None,
        level=level.value if level else None,
        salary_usd_min_minor=_to_usd_minor(salary_usd_min),
        salary_usd_max_minor=_to_usd_minor(salary_usd_max),
    )


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an employee",
)
def create_employee(
    payload: EmployeeCreate,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    """Create a new employee. Currency and employee code are derived server-side."""
    return service.create_employee(payload)


@router.get("", response_model=Page[EmployeeResponse], summary="List employees")
def list_employees(
    service: EmployeeService = Depends(get_employee_service),
    q: str | None = Query(default=None, description="Search name, email, or code."),
    department: Department | None = Query(default=None),
    country: str | None = Query(default=None, min_length=2, max_length=2),
    level: Level | None = Query(default=None),
    salary_usd_min: Decimal | None = Query(default=None, ge=0),
    salary_usd_max: Decimal | None = Query(default=None, ge=0),
    sort_by: SortField = "id",
    sort_dir: SortDirection = "asc",
    cursor: str | None = Query(default=None, description="Opaque next-page cursor."),
    limit: int = Query(default=50, ge=1, le=200),
) -> Page[EmployeeResponse]:
    """Return a cursor-paginated, filtered, sorted page of employees."""
    filters = _build_filters(q, department, country, level, salary_usd_min, salary_usd_max)
    return service.list_employees(
        filters, sort_by=sort_by, sort_dir=sort_dir, cursor=cursor, limit=limit
    )


@router.get("/export", summary="Export employees as CSV")
def export_employees(
    csv_service: EmployeeCsvService = Depends(get_csv_service),
    q: str | None = Query(default=None),
    department: Department | None = Query(default=None),
    country: str | None = Query(default=None, min_length=2, max_length=2),
    level: Level | None = Query(default=None),
    salary_usd_min: Decimal | None = Query(default=None, ge=0),
    salary_usd_max: Decimal | None = Query(default=None, ge=0),
) -> StreamingResponse:
    """Stream the current filtered employee view as a downloadable CSV file."""
    filters = _build_filters(q, department, country, level, salary_usd_min, salary_usd_max)
    return StreamingResponse(
        csv_service.export_csv(filters),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@router.get("/{employee_id}", response_model=EmployeeResponse, summary="Get an employee")
def get_employee(
    employee_id: int,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    """Return a single employee by id."""
    return service.get_employee(employee_id)


@router.patch("/{employee_id}", response_model=EmployeeResponse, summary="Update an employee")
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    """Partially update an employee. Salary normalization is recomputed as needed."""
    return service.update_employee(employee_id, payload)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete an employee",
)
def delete_employee(
    employee_id: int,
    service: EmployeeService = Depends(get_employee_service),
) -> None:
    """Soft-delete an employee (sets ``deleted_at``; the row is retained)."""
    service.delete_employee(employee_id)
