"""initial schema: employees and fx_rates

Revision ID: 0c4e830832b5
Revises: 
Create Date: 2026-06-04 08:45:05.349828
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0c4e830832b5'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('employees',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('employee_code', sa.String(length=16), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('department', sa.String(length=40), nullable=False),
    sa.Column('job_title', sa.String(length=120), nullable=False),
    sa.Column('level', sa.String(length=8), nullable=False),
    sa.Column('employment_type', sa.String(length=20), nullable=False),
    sa.Column('country', sa.String(length=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('base_salary_minor', sa.Integer(), nullable=False),
    sa.Column('base_salary_usd_minor', sa.Integer(), nullable=False),
    sa.Column('hire_date', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_employees_base_salary_usd_minor'), ['base_salary_usd_minor'], unique=False)
        batch_op.create_index(batch_op.f('ix_employees_country'), ['country'], unique=False)
        batch_op.create_index('ix_employees_country_department_level', ['country', 'department', 'level'], unique=False)
        batch_op.create_index(batch_op.f('ix_employees_deleted_at'), ['deleted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_employees_department'), ['department'], unique=False)
        batch_op.create_index(batch_op.f('ix_employees_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_employees_employee_code'), ['employee_code'], unique=True)
        batch_op.create_index(batch_op.f('ix_employees_last_name'), ['last_name'], unique=False)
        batch_op.create_index(batch_op.f('ix_employees_level'), ['level'], unique=False)

    op.create_table('fx_rates',
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('rate_to_usd_micros', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('currency')
    )


def downgrade() -> None:
    # Migrations are forward-only (ADR-0005); downgrades are intentionally unsupported.
    raise NotImplementedError("Downgrades are not supported; migrations are forward-only.")
