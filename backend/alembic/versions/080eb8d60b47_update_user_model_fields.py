"""update_user_model_fields

Revision ID: 080eb8d60b47
Revises: da12af2e9519
Create Date: 2026-09-12 00:06:01.352349

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '080eb8d60b47'
down_revision: Union[str, Sequence[str], None] = 'da12af2e9519'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using batch mode for SQLite and PostgreSQL compatibility."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=False, server_default=''))
        batch_op.drop_index(op.f('ix_users_username'))
        batch_op.drop_column('is_superuser')
        batch_op.drop_column('full_name')
        batch_op.drop_column('username')
        batch_op.drop_column('hashed_password')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hashed_password', sa.VARCHAR(length=255), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('username', sa.VARCHAR(length=50), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('full_name', sa.VARCHAR(length=100), nullable=True))
        batch_op.add_column(sa.Column('is_superuser', sa.BOOLEAN(), nullable=True))
        batch_op.create_index(op.f('ix_users_username'), ['username'], unique=True)
        batch_op.drop_column('password_hash')
        batch_op.drop_column('name')
