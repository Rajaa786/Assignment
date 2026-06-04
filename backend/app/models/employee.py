"""The ``Employee`` ORM model — the persistence shape of an employee record.

Money is stored as **integer minor units** plus an ISO 4217 currency code
(``ADR-0006``); the USD-normalized salary is precomputed on write and indexed so
analytics never recompute FX. Deletes are **soft** (``deleted_at``), and indexes
exist on the columns the list and analytics queries actually filter and group by.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Employee(Base):
    """An employee and their current base salary.

    Salary lives in two integer columns: ``base_salary_minor`` in the employee's
    local ``currency``, and ``base_salary_usd_minor`` normalized to USD for
    cross-country comparison. The normalized value is maintained by the service
    layer on every write, never by the reader.
    """

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)

    department: Mapped[str] = mapped_column(String(40), index=True)
    job_title: Mapped[str] = mapped_column(String(120))
    level: Mapped[str] = mapped_column(String(8), index=True)
    employment_type: Mapped[str] = mapped_column(String(20))

    country: Mapped[str] = mapped_column(String(2), index=True)
    currency: Mapped[str] = mapped_column(String(3))

    base_salary_minor: Mapped[int] = mapped_column()
    base_salary_usd_minor: Mapped[int] = mapped_column(index=True)

    hire_date: Mapped[date] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, index=True
    )

    # Composite index for the analytics group-bys, which slice by these together.
    __table_args__ = (
        Index("ix_employees_country_department_level", "country", "department", "level"),
    )
