"""Reduce embedding dimension from 1536 to 768 for Gemini text-embedding-004

Revision ID: e1f2a3b4c5d6
Revises: d7e8f9a0b1c2
Create Date: 2026-07-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("documents", "embedding", type_=Vector(768))
    op.alter_column("jobs", "embedding", type_=Vector(768))


def downgrade() -> None:
    op.alter_column("documents", "embedding", type_=Vector(1536))
    op.alter_column("jobs", "embedding", type_=Vector(1536))
