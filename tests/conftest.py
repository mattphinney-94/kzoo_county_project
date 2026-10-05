import os

from dotenv import load_dotenv
from fastapi.testclient import TestClient
import pytest



# Load the local development environment before importing
# the FastAPI application.
load_dotenv()


from api.main import app


@pytest.fixture
def client():
    """
    Provide a FastAPI test client for integration tests.
    """

    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def admin_headers():
    """
    Provide authentication headers for administrative
    API integration tests.
    """

    admin_api_key = os.getenv(
        "TREASURY_ADMIN_API_KEY"
    )

    if not admin_api_key:
        pytest.fail(
            "TREASURY_ADMIN_API_KEY is not configured."
        )

    return {
        "X-Admin-Key": admin_api_key
    }