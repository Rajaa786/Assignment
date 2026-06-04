"""Domain identifier types.

``EmployeeId`` is a ``NewType`` over ``int``: it costs nothing at runtime but makes
``def get(employee_id: EmployeeId)`` reject a bare ``int`` at type-check time, so an
employee id can't be confused with any other integer flowing through the system.
"""

from __future__ import annotations

from typing import NewType

EmployeeId = NewType("EmployeeId", int)
