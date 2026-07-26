"""Update embedding dimension to 3072 for gemini-embedding-001

Revision ID: eb9b6f5b4e2e
Revises: e1f2a3b4c5d6
Create Date: 2026-07-26 16:41:19.307661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'eb9b6f5b4e2e'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documents_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_jobs_embedding_hnsw")
    op.alter_column('documents', 'embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=768),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=3072),
               existing_nullable=True)
    op.alter_column('jobs', 'embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=768),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=3072),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('documents', 'embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=3072),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=768),
               existing_nullable=True)
    op.alter_column('jobs', 'embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=3072),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=768),
               existing_nullable=True)
    op.execute("CREATE INDEX idx_documents_embedding_hnsw ON documents USING hnsw (embedding vector_cosine_ops)")
    op.execute("CREATE INDEX idx_jobs_embedding_hnsw ON jobs USING hnsw (embedding vector_cosine_ops)")
