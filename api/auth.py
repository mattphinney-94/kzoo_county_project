import os
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader


ADMIN_API_KEY = os.getenv(
    "TREASURY_ADMIN_API_KEY"
)

if not ADMIN_API_KEY:
    raise RuntimeError(
        "Missing required environment variable: "
        "TREASURY_ADMIN_API_KEY"
    )


admin_api_key_header = APIKeyHeader(
    name="X-Admin-Key",
    auto_error=False
)


def require_admin_api_key(
        api_key: str | None = Security(
            admin_api_key_header
        )
):
    """
    Require the shared administrative API key.

    This mechanism is intended for development or a tightly
    controlled internal deployment. The admin key must not be
    embedded in browser-side code.

    Production deployment should use the County's authentication
    infrastructure so administrative actions can be attributed
    to an authenticated user.
    """

    if (
        api_key is None
        or not secrets.compare_digest(
            api_key,
            ADMIN_API_KEY
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing admin API key."
        )