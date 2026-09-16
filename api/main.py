from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.database import engine


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
# HEALTH CHECK
# ==========================================================

@app.get(
    "/api/health",
    tags=["System"]
)
def health_check():
    """
    Confirm that the API is running and can communicate
    with the MySQL database.
    """

    try:
        with engine.connect() as connection:

            result = connection.execute(
                text("SELECT 1")
            ).scalar_one()

        if result != 1:
            raise HTTPException(
                status_code=503,
                detail="Database health check failed."
            )

        return {
            "status": "healthy",
            "database": "connected"
        }

    except SQLAlchemyError:

        raise HTTPException(
            status_code=503,
            detail="Database connection failed."
        )