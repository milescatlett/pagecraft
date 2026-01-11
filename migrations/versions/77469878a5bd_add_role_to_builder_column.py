"""Add role to builder column

Revision ID: 77469878a5bd
Revises: 
Create Date: 2026-01-11 13:10:27.049062

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77469878a5bd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # The builder_menu_mappings table was created by db.create_all() with the role column
    # This migration serves as a baseline to sync Alembic with the current schema
    pass


def downgrade():
    # Nothing to downgrade - this was a baseline migration
    pass
