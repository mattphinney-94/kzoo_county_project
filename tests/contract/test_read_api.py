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