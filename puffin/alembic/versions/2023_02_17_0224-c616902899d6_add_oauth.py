"""add_oauth

Revision ID: c616902899d6
Revises: be54ab491764
Create Date: 2023-02-17 02:24:48.516153

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c616902899d6'
down_revision = 'be54ab491764'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('oauth1token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_id', sa.Integer(), nullable=False),
    sa.Column('oauth_token', sa.String(), nullable=False),
    sa.Column('oauth_token_secret', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], name=op.f('fk_oauth1token_provider_id_provider')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_oauth1token_user_id_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth1token')),
    sa.UniqueConstraint('provider_id', 'user_id', name=op.f('uq_oauth1token_provider_id'))
    )
    op.create_table('oauth2token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_id', sa.Integer(), nullable=False),
    sa.Column('token_type', sa.String(), nullable=False),
    sa.Column('access_token', sa.String(), nullable=False),
    sa.Column('refresh_token', sa.String(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], name=op.f('fk_oauth2token_provider_id_provider')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_oauth2token_user_id_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth2token')),
    sa.UniqueConstraint('provider_id', 'user_id', name=op.f('uq_oauth2token_provider_id'))
    )


def downgrade() -> None:
    op.drop_table('oauth2token')
    op.drop_table('oauth1token')
