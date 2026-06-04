"""Closed sets of categorical employee attributes.

Departments, levels, and employment types are small, stable vocabularies. Modeling
them as ``StrEnum`` gives the API and seed typed values while persisting as plain
strings — readable in the database and queryable by the NL Q&A feature without a
join. They are domain language, not technical codes (``CLAUDE.md`` §10).
"""

from __future__ import annotations

from enum import StrEnum


class Department(StrEnum):
    """The organizational departments employees belong to."""

    ENGINEERING = "Engineering"
    PRODUCT = "Product"
    SALES = "Sales"
    MARKETING = "Marketing"
    FINANCE = "Finance"
    HUMAN_RESOURCES = "Human Resources"
    SUPPORT = "Support"
    OPERATIONS = "Operations"


class Level(StrEnum):
    """Career levels / pay bands, junior (L1) to principal (L7)."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    L7 = "L7"


class EmploymentType(StrEnum):
    """How an employee is engaged."""

    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
