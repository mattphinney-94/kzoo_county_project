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