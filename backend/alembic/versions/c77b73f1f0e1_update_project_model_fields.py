"""update_project_model_fields

Revision ID: c77b73f1f0e1
Revises: 080eb8d60b47
Create Date: 2026-09-12 00:17:27.000612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c77b73f1f0e1'
down_revision: Union[str, Sequence[str], None] = '080eb8d60b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using batch mode for SQLite and PostgreSQL compatibility."""
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('original_filename', sa.String(length=255), nullable=True))
        batch_op.drop_column('github_url')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('github_url', sa.VARCHAR(length=500), nullable=True))
        batch_op.drop_column('original_filename')
        batch_op.drop_column('source_url')
