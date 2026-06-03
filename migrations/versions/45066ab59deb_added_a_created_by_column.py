"""added a created_by column

Revision ID: 45066ab59deb
Revises: aade676b567e
Create Date: 2026-05-17 10:15:32.467458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45066ab59deb'
down_revision: Union[str, Sequence[str], None] = 'aade676b567e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
   
    op.execute("ALTER TABLE matches ADD COLUMN created_by VARCHAR(50) ")
    op.execute("update  matches set created_by=(ARRAY['association1','association2','association3','association4','association5'])[floor(random()*5 + 1)::int] from generate_series(0,500) where created_by is null")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("alter table matches drop column created_by")
    pass
