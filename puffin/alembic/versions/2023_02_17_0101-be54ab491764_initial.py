"""initial

Revision ID: be54ab491764
Revises: 
Create Date: 2023-02-17 01:01:06.800022

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'be54ab491764'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('audit_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('old_data', sa.JSON(), nullable=True),
    sa.Column('new_data', sa.JSON(), nullable=True),
    sa.Column('table_name', sa.String(), nullable=False),
    sa.Column('row_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.Enum('UPDATE', 'INSERT', 'DELETE', name='logtype'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_table('course',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('expiry_date', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_course'))
    )
    op.create_table('provider',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('has_ref_id', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider'))
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('firstname', sa.String(), nullable=False),
    sa.Column('lastname', sa.String(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), server_default=sa.text('(FALSE)'), nullable=False),
    sa.Column('expiry_date', sa.DateTime(), nullable=True),
    sa.Column('password', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user'))
    )
    op.create_table('account',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('ref_id', sa.Integer(), nullable=True),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('expiry_date', sa.DateTime(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('fullname', sa.String(), nullable=False),
    sa.Column('note', sa.String(), nullable=True),
    sa.Column('avatar_url', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], name=op.f('fk_account_provider_id_provider')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_account_user_id_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_account')),
    sa.UniqueConstraint('username', name=op.f('uq_account_username'))
    )
    op.create_table('enrollment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['course.id'], name=op.f('fk_enrollment_course_id_course')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_enrollment_user_id_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_enrollment')),
    sa.UniqueConstraint('user_id', 'course_id', name=op.f('uq_enrollment_user_id'))
    )
    op.create_table('subgroup',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('external_id', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('join_model', sa.Enum('RESTRICTED', 'OPEN', 'AUTO', 'CLOSED', name='joinmodel'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['course.id'], name=op.f('fk_subgroup_course_id_course')),
    sa.ForeignKeyConstraint(['parent_id'], ['subgroup.id'], name=op.f('fk_subgroup_parent_id_subgroup')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subgroup')),
    sa.UniqueConstraint('course_id', 'slug', name=op.f('uq_subgroup_course_id'))
    )
    op.create_table('membership',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['subgroup.id'], name=op.f('fk_membership_group_id_subgroup')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_membership_user_id_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_membership')),
    sa.UniqueConstraint('user_id', 'group_id', name=op.f('uq_membership_user_id'))
    )


def downgrade() -> None:
    op.drop_table('membership')
    op.drop_table('subgroup')
    op.drop_table('enrollment')
    op.drop_table('account')
    op.drop_table('user')
    op.drop_table('provider')
    op.drop_table('course')
    op.drop_table('audit_log')
