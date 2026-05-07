"""partition audit_logs table

Revision ID: 0002_partition_audit_logs
Revises: 0001_create_audit_logs
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_partition_audit_logs'
down_revision = '0001_create_audit_logs'
branch_labels = None
depends_on = None


def upgrade():
    # Create a new partitioned table and move existing data into a default partition.
    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs_partitioned (
        id BIGINT PRIMARY KEY,
        actor_id VARCHAR(128),
        action VARCHAR(64) NOT NULL,
        resource_type VARCHAR(128),
        resource_id VARCHAR(128),
        before JSON,
        after JSON,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        deleted_at TIMESTAMPTZ
    ) PARTITION BY RANGE (created_at);
    """)

    # Create a default partition that covers all existing data range
    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs_p_default PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('1970-01-01') TO ('9999-12-31');
    """)

    # Move data from old audit_logs into partitioned table (if exists)
    op.execute("""
    INSERT INTO audit_logs_partitioned (id, actor_id, action, resource_type, resource_id, before, after, created_at, deleted_at)
    SELECT id, actor_id, action, resource_type, resource_id, before, after, created_at, deleted_at
    FROM audit_logs;
    """)

    # Drop old table and rename partitioned to original name
    op.execute("""
    DROP TABLE IF EXISTS audit_logs CASCADE;
    ALTER TABLE audit_logs_partitioned RENAME TO audit_logs;
    """)

    # Recreate index on created_at for partitioned table
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at);")


def downgrade():
    # Recreate non-partitioned table and move data back
    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs_old (
        id BIGINT PRIMARY KEY,
        actor_id VARCHAR(128),
        action VARCHAR(64) NOT NULL,
        resource_type VARCHAR(128),
        resource_id VARCHAR(128),
        before JSON,
        after JSON,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        deleted_at TIMESTAMPTZ
    );
    """)

    op.execute("INSERT INTO audit_logs_old SELECT * FROM audit_logs;")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE;")
    op.execute("ALTER TABLE audit_logs_old RENAME TO audit_logs;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at);")