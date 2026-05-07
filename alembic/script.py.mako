% from alembic import util
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | commajoin}
Create Date: ${create_date}
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    ${upgrades if upgrades else 'pass'}

def downgrade():
    ${downgrades if downgrades else 'pass'}
