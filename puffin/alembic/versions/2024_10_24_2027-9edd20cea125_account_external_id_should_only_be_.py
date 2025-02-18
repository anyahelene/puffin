"""account.external_id should only be unique per provider

Revision ID: 9edd20cea125
Revises: 8741313faa9c
Create Date: 2024-10-24 20:27:08.981789

"""
from alembic import op
import sqlalchemy as sa
from puffin.db import database


# revision identifiers, used by Alembic.
revision = '9edd20cea125'
down_revision = '8741313faa9c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('account') as batch_op:
        database._viewmeta.drop_all(database.engine)
        batch_op.drop_constraint('uq_account_external_id',  type_='unique')
        batch_op.create_unique_constraint(op.f('uq_account_provider_name'),  ['provider_name', 'external_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('account') as batch_op:
        database._viewmeta.drop_all(database.engine)
        batch_op.drop_constraint(op.f('uq_account_provider_name'), type_='unique')
        batch_op.create_unique_constraint('uq_account_external_id', ['external_id'])
    # ### end Alembic commands ###
