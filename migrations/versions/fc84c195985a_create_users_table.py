"""create users table

Revision ID: fc84c195985a
Revises: ae9f5ea7bd9a
Create Date: 2020-01-04 20:20:53.539569

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "fc84c195985a"
down_revision = "ae9f5ea7bd9a"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "users",
        sa.Column("pk", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("pk"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    # ### end Alembic commands ###
