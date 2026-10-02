"""Add embedding vector column to document chunk

Revision ID: eb6f038d729c
Revises: 01a25b7bc66b
Create Date: 2026-10-02 01:39:24.982907

"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'eb6f038d729c'
down_revision = '01a25b7bc66b'
branch_labels = None
depends_on = None

# Frozen at the model's dimensions when this revision was written (bge-small-en-v1.5).
EMBEDDING_DIMENSIONS = 384


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        'documentchunk',
        sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=False),
    )


def downgrade():
    op.drop_column('documentchunk', 'embedding')
