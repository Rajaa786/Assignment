"""CSV import endpoint.

Accepts a multipart file upload, runs validation (optionally dry-run), and returns a
structured :class:`ImportResult`. The heavy lifting — validation, all-or-nothing bulk
insert — lives in the service; this layer only handles the HTTP file plumbing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.dependencies import get_csv_service
from app.schemas.imports import ImportResult
from app.services.csv_service import EmployeeCsvService

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/employees", response_model=ImportResult, summary="Bulk import employees from CSV")
async def import_employees(
    file: UploadFile = File(description="UTF-8 CSV with the employee columns."),
    dry_run: bool = Query(default=False, description="Validate only; do not persist."),
    service: EmployeeCsvService = Depends(get_csv_service),
) -> ImportResult:
    """Import employees from an uploaded CSV (all-or-nothing; supports dry-run preview)."""
    content = await file.read()
    return service.import_employees(content, dry_run=dry_run)
