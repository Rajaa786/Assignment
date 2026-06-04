"""ORM models package.

Importing this package registers every model on ``Base.metadata`` so Alembic
autogeneration and test fixtures see the full schema.
"""

from app.models.employee import Employee
from app.models.fx_rate import FxRate

__all__ = ["Employee", "FxRate"]
