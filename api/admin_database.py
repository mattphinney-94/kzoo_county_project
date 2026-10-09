import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL


DB_HOST = os.getenv("TREASURY_DB_HOST")

DB_PORT = int(
    os.getenv(
        "TREASURY_DB_PORT",
        "3306"
    )
)

DB_NAME = os.getenv("TREASURY_DB_NAME")

ADMIN_DB_USER = os.getenv(
    "TREASURY_ADMIN_DB_USER"
)

ADMIN_DB_PASSWORD = os.getenv(
    "TREASURY_ADMIN_DB_PASSWORD"
)


required_settings = {
    "TREASURY_DB_HOST": DB_HOST,
    "TREASURY_DB_NAME": DB_NAME,
    "TREASURY_ADMIN_DB_USER": ADMIN_DB_USER,
    "TREASURY_ADMIN_DB_PASSWORD": ADMIN_DB_PASSWORD
}


missing_settings = [
    setting_name
    for setting_name, setting_value
    in required_settings.items()
    if not setting_value
]


if missing_settings:
    raise RuntimeError(
        "Missing required admin database environment variables: "
        f"{', '.join(missing_settings)}"
    )


admin_database_url = URL.create(
    drivername="mysql+pymysql",
    username=ADMIN_DB_USER,
    password=ADMIN_DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)


admin_engine = create_engine(
    admin_database_url,
    pool_pre_ping=True,
    hide_parameters=True
)