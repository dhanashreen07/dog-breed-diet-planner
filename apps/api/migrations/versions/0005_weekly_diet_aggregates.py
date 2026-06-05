"""Add weekly aggregate columns to diet_plans table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-05 14:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add weekly aggregate columns to diet_plans
    op.add_column(
        "diet_plans",
        sa.Column("weekly_calories", sa.Integer(), nullable=True),
    )
    op.add_column(
        "diet_plans",
        sa.Column("weekly_protein_g", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "diet_plans",
        sa.Column("weekly_fat_g", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "diet_plans",
        sa.Column("weekly_carbs_g", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "diet_plans",
        sa.Column("meals_per_week", sa.Integer(), nullable=True),
    )

    # Populate weekly columns from daily values for existing records
    op.execute("""
        UPDATE diet_plans
        SET 
            weekly_calories = daily_calories * 7,
            weekly_protein_g = protein_g * 7,
            weekly_fat_g = fat_g * 7,
            weekly_carbs_g = carbs_g * 7,
            meals_per_week = meals_per_day * 7
        WHERE weekly_calories IS NULL
    """)

    # Make columns NOT NULL after population
    op.alter_column(
        "diet_plans",
        "weekly_calories",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "diet_plans",
        "weekly_protein_g",
        existing_type=sa.Numeric(8, 2),
        nullable=False,
    )
    op.alter_column(
        "diet_plans",
        "weekly_fat_g",
        existing_type=sa.Numeric(8, 2),
        nullable=False,
    )
    op.alter_column(
        "diet_plans",
        "weekly_carbs_g",
        existing_type=sa.Numeric(8, 2),
        nullable=False,
    )
    op.alter_column(
        "diet_plans",
        "meals_per_week",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    # Remove weekly columns
    op.drop_column("diet_plans", "weekly_calories")
    op.drop_column("diet_plans", "weekly_protein_g")
    op.drop_column("diet_plans", "weekly_fat_g")
    op.drop_column("diet_plans", "weekly_carbs_g")
    op.drop_column("diet_plans", "meals_per_week")
