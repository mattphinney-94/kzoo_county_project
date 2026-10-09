from unittest.mock import MagicMock

import pytest

from api.routers import associations as associations_router
from api.routers import entities as entities_router

# ==========================================================
# SYSTEM
# ==========================================================

def test_health_check(client):

    response = client.get(
        "/api/health"
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "status": "healthy",
        "database": "connected"
    }


# ==========================================================
# ENTITY SEARCH
# ==========================================================

def test_search_requires_query(client):

    response = client.get(
        "/api/entities/search"
    )

    assert response.status_code == 422


def test_search_rejects_blank_query(client):

    response = client.get(
        "/api/entities/search",
        params={
            "q": "   "
        }
    )

    assert response.status_code == 400


def test_search_limit_validation(client):

    response = client.get(
        "/api/entities/search",
        params={
            "q": "graham",
            "limit": 0
        }
    )

    assert response.status_code == 422

    response = client.get(
        "/api/entities/search",
        params={
            "q": "graham",
            "limit": 101
        }
    )

    assert response.status_code == 422

def test_search_treats_like_wildcards_as_literals(
        client,
        monkeypatch
):
    """
    Percent signs and underscores supplied by the user
    should be treated as literal search characters rather
    than SQL LIKE wildcards.
    """

    search_result = MagicMock()

    search_result.mappings.return_value.all.return_value = []

    mock_connection = MagicMock()

    mock_connection.execute.return_value = (
        search_result
    )

    mock_engine = MagicMock()

    mock_engine.connect.return_value.__enter__.return_value = (
        mock_connection
    )

    monkeypatch.setattr(
        entities_router,
        "engine",
        mock_engine
    )

    response = client.get(
        "/api/entities/search",
        params={
            "q": "%_!"
        }
    )

    assert response.status_code == 200

    execute_call = (
        mock_connection.execute.call_args
    )

    query = str(
        execute_call.args[0]
    )

    parameters = (
        execute_call.args[1]
    )

    assert parameters[
        "normalized_term"
    ] == "%_!"

    assert parameters[
        "contains_pattern"
    ] == "%!%!_!!%"

    assert parameters[
        "prefix_pattern"
    ] == "!%!_!!%"

    assert query.count(
        "ESCAPE '!'"
    ) == 4

# ==========================================================
# ENTITY DETAIL
# ==========================================================

def test_nonexistent_entity_returns_404(client):

    response = client.get(
        "/api/entities/99999999"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Entity not found."
    }


def test_invalid_entity_id_returns_422(client):

    response = client.get(
        "/api/entities/not-an-integer"
    )

    assert response.status_code == 422


# ==========================================================
# ENTITY PARCELS
# ==========================================================

def test_nonexistent_entity_parcels_return_404(client):

    response = client.get(
        "/api/entities/99999999/parcels"
    )

    assert response.status_code == 404

def test_entity_parcels_allows_nullable_numeric_fields(
        client,
        monkeypatch
):
    """
    Parcel numeric fields that are nullable in MySQL
    should also be nullable in the API response schema.
    """

    entity_exists_result = MagicMock()

    entity_exists_result.first.return_value = (
        1,
    )

    parcel_result = MagicMock()

    parcel_result.mappings.return_value.all.return_value = [
        {
            "parcel_number":
                "TEST-001",

            "property_address":
                None,

            "role":
                "Owner",

            "principal_residence_exemption_percentage":
                None,

            "property_class":
                None,

            "tax_value":
                None,

            "assessed_value":
                None,

            "state_equalized_value":
                None
        }
    ]

    mock_connection = MagicMock()

    mock_connection.execute.side_effect = [
        entity_exists_result,
        parcel_result
    ]

    mock_engine = MagicMock()

    mock_engine.connect.return_value.__enter__.return_value = (
        mock_connection
    )

    monkeypatch.setattr(
        entities_router,
        "engine",
        mock_engine
    )

    response = client.get(
        "/api/entities/1/parcels"
    )

    assert response.status_code == 200

    data = response.json()

    assert data[
        "parcel_count"
    ] == 1

    parcel = data[
        "parcels"
    ][0]

    assert (
        parcel[
            "principal_residence_exemption_percentage"
        ]
        is None
    )

    assert parcel[
        "tax_value"
    ] is None

    assert parcel[
        "assessed_value"
    ] is None

    assert parcel[
        "state_equalized_value"
    ] is None


# ==========================================================
# ENTITY ASSOCIATIONS
# ==========================================================

def test_nonexistent_entity_associations_return_404(
        client
):

    response = client.get(
        "/api/entities/99999999/associations"
    )

    assert response.status_code == 404

@pytest.mark.parametrize(
    (
        "router_module",
        "path"
    ),
    [
        (
            entities_router,
            "/api/entities/1/associations"
        ),
        (
            associations_router,
            "/api/associations/1/evidence"
        )
    ]
)
def test_association_endpoints_require_active_snapshot(
        client,
        monkeypatch,
        router_module,
        path
):
    """
    Association data must not be returned when the API
    cannot determine which snapshot's suppressions apply.
    """

    mock_connection = MagicMock()

    mock_engine = MagicMock()

    mock_engine.connect.return_value.__enter__.return_value = (
        mock_connection
    )

    monkeypatch.setattr(
        router_module,
        "engine",
        mock_engine
    )

    monkeypatch.setattr(
        router_module,
        "get_active_snapshot_id",
        lambda connection: None
    )

    response = client.get(
        path
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail":
            "No active data snapshot is configured."
    }


# ==========================================================
# ASSOCIATION EVIDENCE
# ==========================================================

def test_nonexistent_association_returns_404(client):

    response = client.get(
        "/api/associations/99999999/evidence"
    )

    assert response.status_code == 404


def test_invalid_association_id_returns_422(client):

    response = client.get(
        "/api/associations/not-an-integer/evidence"
    )

    assert response.status_code == 422