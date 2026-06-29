"""Add soft delete to jobs and unique constraint on interview rounds

Revision ID: c1a2b3d4e5f6
Revises: b52756b59faa
Create Date: 2025-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "b52756b59faa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SOFT-01: Add soft delete columns to jobs table
    op.add_column("jobs", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("jobs", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # FIX-05: Add unique constraint on interview_rounds (application_id, round_number)
    op.create_unique_constraint(
        "uq_interview_rounds_application_round",
        "interview_rounds",
        ["application_id", "round_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_interview_rounds_application_round", "interview_rounds", type_="unique")
    op.drop_column("jobs", "deleted_at")
    op.drop_column("jobs", "is_deleted")
