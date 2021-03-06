import databases
import pendulum
import sqlalchemy

from settings import DATABASE_URL, TEST_DATABASE_URL, TESTING

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
    sqlalchemy.Column("email", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("password", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=sqlalchemy.func.now(), nullable=False),
    sqlalchemy.Column("last_login", sqlalchemy.DateTime),
)

if TESTING:
    database = databases.Database(TEST_DATABASE_URL, force_rollback=True)
else:
    database = databases.Database(DATABASE_URL)
