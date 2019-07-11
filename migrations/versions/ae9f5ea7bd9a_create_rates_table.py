"""create rates table

Revision ID: ae9f5ea7bd9a
Revises: 
Create Date: 2019-07-11 11:07:50.885209

"""
import sqlalchemy

from alembic import op


# revision identifiers, used by Alembic.
revision = "ae9f5ea7bd9a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rates",
        sqlalchemy.Column("date", sqlalchemy.Date, primary_key=True),
        sqlalchemy.Column("rates", sqlalchemy.JSON),
    )


def downgrade():
    op.drop_table("account")
