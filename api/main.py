from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.database import (
    engine,
    get_active_snapshot_id
)
from api.routers import (
    admin,
    associations,
    entities
)

import logging
logger = logging.getLogger(__name__)


# ==========================================================
# FASTAPI APPLICATION
# ==========================================================

app = FastAPI(
    title="Kalamazoo County Treasury API",
    description=(
        "API for retrieving parcel, entity, and "
        "entity-association information."
    ),
    version="0.1.0"
)


# ==========================================================
# ROUTERS
# ==========================================================

app.include_router(
    entities.router
)

app.include_router(
    associations.router
)

app.include_router(
    admin.router
)


# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.get(
    "/api/health",
    tags=["System"]
)
def health_check():
    """
    Confirm that the API is running, can communicate with
    MySQL, and has an active data snapshot.
    """

    try:
        with engine.connect() as connection:

            database_result = connection.execute(
                text("SELECT 1")
            ).scalar_one()

            if database_result != 1:
                raise HTTPException(
                    status_code=503,
                    detail="Database health check failed."
                )

            active_snapshot_id = (
                get_active_snapshot_id(
                    connection
                )
            )

            if active_snapshot_id is None:
                raise HTTPException(
                    status_code=503,
                    detail="No active data snapshot is configured."
                )

        return {
            "status": "healthy",
            "database": "connected"
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        logger.exception(
            "Database connection failed."
        )
        raise HTTPException(
            status_code=503,
            detail="Database connection failed."
        )
