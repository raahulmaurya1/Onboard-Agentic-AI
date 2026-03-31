"""Add multiple account types constraints

Revision ID: a1b2c3d4e5f6
Revises: 5d971737cc6a
Create Date: 2026-03-29 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5d971737cc6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop existing unique indexes on phone and email
    op.drop_index('ix_user_initial_phone', table_name='user_initial')
    op.drop_index('ix_user_initial_email', table_name='user_initial')

    # 2. Re-create them as standard non-unique indexes
    op.create_index('ix_user_initial_phone', 'user_initial', ['phone'], unique=False)
    op.create_index('ix_user_initial_email', 'user_initial', ['email'], unique=False)

    # 3. Create scoping composites unique constraints with account_type
    op.create_unique_constraint('uq_phone_account_type', 'user_initial', ['phone', 'account_type'])
    op.create_unique_constraint('uq_email_account_type', 'user_initial', ['email', 'account_type'])


def downgrade() -> None:
    op.drop_constraint('uq_phone_account_type', 'user_initial', type_='unique')
    op.drop_constraint('uq_email_account_type', 'user_initial', type_='unique')

    op.drop_index('ix_user_initial_phone', table_name='user_initial')
    op.drop_index('ix_user_initial_email', table_name='user_initial')

    op.create_index('ix_user_initial_phone', 'user_initial', ['phone'], unique=True)
    op.create_index('ix_user_initial_email', 'user_initial', ['email'], unique=True)
