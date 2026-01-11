"""Add is_sticky to menus

Revision ID: 39d5c1b68320
Revises: 77469878a5bd
Create Date: 2026-01-11 13:32:16.303798

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '39d5c1b68320'
down_revision = '77469878a5bd'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('menus', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_sticky', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('menus', schema=None) as batch_op:
        batch_op.drop_column('is_sticky')
