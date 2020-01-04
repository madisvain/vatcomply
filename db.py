import databases
import pendulum
import sqlalchemy

from settings import DATABASE_URL

metadata = sqlalchemy.MetaData()

Rates = sqlalchemy.Table(
    "rates",
    metadata,
    sqlalchemy.Column("date", sqlalchemy.Date, primary_key=True),
    sqlalchemy.Column("rates", sqlalchemy.JSON),
)

Users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("pk", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String, nullable=False, index=True),
    sqlalchemy.Column("password", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=pendulum.now(), nullable=False),
    sqlalchemy.Column("last_login", sqlalchemy.DateTime),
)

database = databases.Database(DATABASE_URL)
