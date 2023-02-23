"""group_join_model_source

Revision ID: 5fecaca6bfc1
Revises: c616902899d6
Create Date: 2023-02-21 05:18:03.791588

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5fecaca6bfc1'
down_revision = 'c616902899d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('membership', sa.Column('join_model', sa.Enum('RESTRICTED', 'OPEN', 'AUTO', 'CLOSED', name='joinmodel'), nullable=True))
    op.add_column('subgroup', sa.Column('join_source', sa.String(), nullable=True))
    op.execute("UPDATE membership SET join_model = subgroup.join_model FROM subgroup WHERE subgroup.id = membership.group_id AND membership.join_model IS NULL;")

def downgrade() -> None:
    op.drop_column('subgroup', 'join_source')
    op.drop_column('membership', 'join_model')
