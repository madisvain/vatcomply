import databases
import sqlalchemy

from settings import DATABASE_URL

metadata = sqlalchemy.MetaData()

Rates = sqlalchemy.Table(
    "rates",
    metadata,
    sqlalchemy.Column("date", sqlalchemy.Date, primary_key=True),
    sqlalchemy.Column("rates", sqlalchemy.JSON),
)

database = databases.Database(DATABASE_URL)
