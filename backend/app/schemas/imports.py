"""Transport schemas for CSV import results.

The import is **all-or-nothing**: if any row fails validation, nothing is persisted
and every error is reported with its row number, so the HR manager can fix the
spreadsheet and retry. ``dry_run`` runs the same validation without writing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImportRowError(BaseModel):
    """A validation failure for one CSV row."""

    row_number: int = Field(description="1-based row number in the data (excludes the header).")
    field: str | None = Field(default=None, description="The offending field, if known.")
    message: str = Field(description="Human-readable reason the row was rejected.")


class ImportResult(BaseModel):
    """Outcome of a CSV import or dry-run preview."""

    total: int = Field(description="Number of data rows read.")
    valid: int = Field(description="Rows that passed validation.")
    failed: int = Field(description="Rows that failed validation.")
    inserted: int = Field(description="Rows actually persisted (0 on dry-run or any failure).")
    dry_run: bool = Field(description="Whether this was a validation-only preview.")
    errors: list[ImportRowError] = Field(default_factory=list)
