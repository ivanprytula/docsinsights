"""Add role field to User

Revision ID: 7343723f28b8
Revises: 1f55f0997689
Create Date: 2026-09-29 01:39:06.364398

"""
from alembic import op
import sqlalchemy as sa


revision = '7343723f28b8'
down_revision = '1f55f0997689'
branch_labels = None
depends_on = None


def upgrade():
    sa.Enum('user', 'admin', name='userrole').create(op.get_bind(), checkfirst=True)
    op.add_column('user', sa.Column('role', sa.Enum('user', 'admin', name='userrole'), nullable=False, server_default='user'))


def downgrade():
    op.drop_column('user', 'role')
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
