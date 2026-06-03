"""adding index to player_stats table

Revision ID: cc8fa4409773
Revises: 45066ab59deb
Create Date: 2026-05-17 10:55:50.107910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc8fa4409773'
down_revision: Union[str, Sequence[str], None] = '45066ab59deb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
