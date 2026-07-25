"""Add pgvector extension and RAG fields to documents/jobs

Revision ID: d7e8f9a0b1c2
Revises: c1a2b3d4e5f6
Create Date: 2025-07-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add RAG fields to documents table
    op.add_column("documents", sa.Column("parsed_data", sa.JSON(), nullable=True))
    op.add_column("documents", sa.Column("embedding", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("parsed_at", sa.DateTime(), nullable=True))

    # Add embedding field to jobs table
    op.add_column("jobs", sa.Column("embedding", sa.Text(), nullable=True))

    # Recreate embedding columns with proper Vector type using raw SQL
    op.execute("ALTER TABLE documents DROP COLUMN embedding")
    op.execute("ALTER TABLE documents ADD COLUMN embedding vector(1536)")

    op.execute("ALTER TABLE jobs DROP COLUMN embedding")
    op.execute("ALTER TABLE jobs ADD COLUMN embedding vector(1536)")

    # Create HNSW indexes for fast similarity search
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw "
        "ON documents USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw "
        "ON jobs USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_embedding_hnsw", table_name="jobs")
    op.drop_index("idx_documents_embedding_hnsw", table_name="documents")
    op.drop_column("jobs", "embedding")
    op.drop_column("documents", "embedding")
    op.drop_column("documents", "parsed_at")
    op.drop_column("documents", "parsed_data")
    op.execute("DROP EXTENSION IF EXISTS vector")
