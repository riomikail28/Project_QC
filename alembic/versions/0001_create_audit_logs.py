"""create audit_logs table

Revision ID: 0001_create_audit_logs
Revises: 
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_create_audit_logs'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('actor_id', sa.String(length=128), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=128), nullable=True),
        sa.Column('resource_id', sa.String(length=128), nullable=True),
        sa.Column('before', sa.JSON, nullable=True),
        sa.Column('after', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade():
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_table('audit_logs')
