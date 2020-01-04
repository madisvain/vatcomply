"""create rates table

Revision ID: ae9f5ea7bd9a
Revises: 
Create Date: 2019-07-11 11:07:50.885209

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ae9f5ea7bd9a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("rates", sa.Column("date", sa.Date, primary_key=True), sa.Column("rates", sa.JSON))


def downgrade():
    op.drop_table("rates")
