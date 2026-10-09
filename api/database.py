import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import logging
logger = logging.getLogger(__name__)


# ==========================================================
# DATABASE CONFIGURATION
# ==========================================================

DB_HOST = os.getenv(
    "TREASURY_DB_HOST"
)

DB_PORT = int(
    os.getenv(
        "TREASURY_DB_PORT",
        "3306"
    )
)

DB_NAME = os.getenv(
    "TREASURY_DB_NAME"
)

DB_USER = os.getenv(
    "TREASURY_DB_USER"
)

DB_PASSWORD = os.getenv(
    "TREASURY_DB_PASSWORD"
)


# ==========================================================
# CONFIGURATION VALIDATION
# ==========================================================

required_settings = {
    "TREASURY_DB_HOST": DB_HOST,
    "TREASURY_DB_NAME": DB_NAME,
    "TREASURY_DB_USER": DB_USER,
    "TREASURY_DB_PASSWORD": DB_PASSWORD
}

missing_settings = [
    setting_name
    for setting_name, setting_value
    in required_settings.items()
    if not setting_value
]

if missing_settings:
    raise RuntimeError(
        "Missing required database environment variables: "
        f"{', '.join(missing_settings)}"
    )


# ==========================================================
# SQLALCHEMY ENGINE
# ==========================================================

database_url = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)


engine = create_engine(
    database_url,
    pool_pre_ping=True,
    hide_parameters=True
)

ACTIVE_SNAPSHOT_QUERY = text(
    """
    SELECT snapshot_id
    FROM active_data_snapshot
    WHERE singleton_id = 1
    """
)


def get_active_snapshot_id(connection):
    """
    Return the currently active data snapshot ID,
    or None if no active snapshot is configured.
    """

    return (
        connection.execute(
            ACTIVE_SNAPSHOT_QUERY
        )
        .scalar_one_or_none()
    )