"""Verify the Alembic migrations build the expected schema from scratch.

Runs the real ``alembic upgrade head`` against a throwaway SQLite file — the same
command a developer or CI runs — and asserts the tables and a representative
composite index exist. This guards against the migration drifting from the models.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[2]


def test_upgrade_head_creates_expected_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "migration_test.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    inspector = inspect(create_engine(f"sqlite:///{db_path}"))
    tables = set(inspector.get_table_names())
    assert {"employees", "fx_rates", "alembic_version"} <= tables

    employee_indexes = {index["name"] for index in inspector.get_indexes("employees")}
    assert "ix_employees_country_department_level" in employee_indexes
    assert "ix_employees_base_salary_usd_minor" in employee_indexes
