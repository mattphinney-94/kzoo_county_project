from collections import Counter


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

def test_entity_search_returns_results(client):

    response = client.get(
        "/api/entities/search",
        params={
            "q": "graham"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "graham"

    assert (
        data["result_count"]
        ==
        len(data["results"])
    )

    assert data["result_count"] > 0

    entity_ids = [
        result["entity_id"]
        for result in data["results"]
    ]

    # Search should return one row per resolved entity.
    assert (
        len(entity_ids)
        ==
        len(set(entity_ids))
    )


def test_source_name_variant_is_searchable(client):

    response = client.get(
        "/api/entities/search",
        params={
            "q": "coppercreek"
        }
    )

    assert response.status_code == 200

    data = response.json()

    matching_entities = [
        result
        for result in data["results"]
        if result["entity_id"] == 4342
    ]

    assert len(matching_entities) == 1

    entity = matching_entities[0]

    assert (
        entity["canonical_name"]
        ==
        "THE COPPER CREEK TRUST"
    )


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

def test_entity_detail(client):

    response = client.get(
        "/api/entities/1719"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["entity_id"] == 1719

    assert (
        data["canonical_name"]
        ==
        "GRAHAM, WILLIAM D"
    )

    assert data["entity_type"] == "Person"

    assert data["occurrence_count"] == 6


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

def test_entity_parcels(client):

    response = client.get(
        "/api/entities/1719/parcels"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["entity_id"] == 1719

    assert data["parcel_count"] == 6

    assert (
        data["parcel_count"]
        ==
        len(data["parcels"])
    )

    parcel_numbers = {
        parcel["parcel_number"]
        for parcel in data["parcels"]
    }

    expected_parcels = {
        "07-24-201-591",
        "07-24-201-601",
        "07-24-215-090",
        "07-24-215-100",
        "07-24-215-110",
        "07-24-215-160"
    }

    assert (
        parcel_numbers
        ==
        expected_parcels
    )

    for parcel in data["parcels"]:

        assert parcel["roles"] == [
            "Owner"
        ]


def test_copper_creek_parcels_are_grouped_by_parcel(client):

    response = client.get(
        "/api/entities/4342/parcels"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parcel_count"] == 7

    parcel_numbers = [
        parcel["parcel_number"]
        for parcel in data["parcels"]
    ]

    assert (
        len(parcel_numbers)
        ==
        len(set(parcel_numbers))
    )

    for parcel in data["parcels"]:

        assert set(parcel["roles"]) == {
            "Owner",
            "Tax Send To",
            "Taxpayer"
        }


def test_nonexistent_entity_parcels_return_404(client):

    response = client.get(
        "/api/entities/99999999/parcels"
    )

    assert response.status_code == 404


# ==========================================================
# ENTITY ASSOCIATIONS
# ==========================================================

def test_william_graham_association(client):

    response = client.get(
        "/api/entities/1719/associations"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["entity_id"] == 1719
    assert data["association_count"] == 1

    association = data[
        "associations"
    ][0]

    assert association[
        "association_id"
    ] == 173

    assert association[
        "associated_entity_id"
    ] == 4342

    assert (
        association[
            "associated_canonical_name"
        ]
        ==
        "THE COPPER CREEK TRUST"
    )

    assert (
        association[
            "association_confidence"
        ]
        ==
        "High"
    )

    assert association[
        "evidence_count"
    ] == 20

    assert association[
        "evidence_rule_count"
    ] == 5


def test_association_is_directionally_symmetric(client):

    william_response = client.get(
        "/api/entities/1719/associations"
    )

    copper_response = client.get(
        "/api/entities/4342/associations"
    )

    assert william_response.status_code == 200
    assert copper_response.status_code == 200

    william_association = (
        william_response
        .json()[
            "associations"
        ][0]
    )

    copper_association = next(
        association
        for association
        in copper_response.json()[
            "associations"
        ]
        if association[
            "associated_entity_id"
        ] == 1719
    )

    assert (
        william_association[
            "association_id"
        ]
        ==
        copper_association[
            "association_id"
        ]
        ==
        173
    )

    assert (
        william_association[
            "association_confidence"
        ]
        ==
        copper_association[
            "association_confidence"
        ]
        ==
        "High"
    )

    assert (
        william_association[
            "evidence_count"
        ]
        ==
        copper_association[
            "evidence_count"
        ]
        ==
        20
    )

    assert (
        william_association[
            "evidence_rule_count"
        ]
        ==
        copper_association[
            "evidence_rule_count"
        ]
        ==
        5
    )


def test_associations_are_ordered_by_confidence(client):

    response = client.get(
        "/api/entities/4342/associations"
    )

    assert response.status_code == 200

    associations = (
        response.json()[
            "associations"
        ]
    )

    confidence_rank = {
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    ordering = [
        (
            confidence_rank[
                association[
                    "association_confidence"
                ]
            ],
            -association[
                "evidence_count"
            ],
            -association[
                "evidence_rule_count"
            ],
            association[
                "associated_canonical_name"
            ],
            association[
                "associated_entity_id"
            ]
        )
        for association
        in associations
    ]

    assert ordering == sorted(
        ordering
    )


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

def test_association_evidence(client):

    response = client.get(
        "/api/associations/173/evidence"
    )

    assert response.status_code == 200

    data = response.json()

    assert data[
        "association_id"
    ] == 173

    assert data[
        "entity_a"
    ] == {
        "entity_id": 1719,
        "canonical_name":
            "GRAHAM, WILLIAM D",
        "entity_type": "Person"
    }

    assert data[
        "entity_b"
    ] == {
        "entity_id": 4342,
        "canonical_name":
            "THE COPPER CREEK TRUST",
        "entity_type": "Organization"
    }

    assert (
        data[
            "association_confidence"
        ]
        ==
        "High"
    )

    assert data[
        "evidence_count"
    ] == 20

    assert data[
        "evidence_rule_count"
    ] == 5

    assert (
        len(data["evidence"])
        ==
        data["evidence_count"]
    )


def test_association_evidence_rule_counts(client):

    response = client.get(
        "/api/associations/173/evidence"
    )

    assert response.status_code == 200

    evidence = (
        response.json()[
            "evidence"
        ]
    )

    rule_counts = Counter(
        row["evidence_rule"]
        for row in evidence
    )

    expected_rule_counts = Counter({
        "SAME_PARCEL_CO_OWNER":
            6,

        "SAME_PARCEL_ORG_TAXPAYER_PERSON_OWNER":
            6,

        "SAME_PARCEL_ORG_TAX_SEND_TO_PERSON_OWNER":
            6,

        "SHARED_OWNER_ADDRESS":
            1,

        "SHARED_TAXPAYER_ADDRESS":
            1
    })

    assert (
        rule_counts
        ==
        expected_rule_counts
    )

    assert (
        len(rule_counts)
        ==
        5
    )


def test_evidence_ids_are_unique(client):

    response = client.get(
        "/api/associations/173/evidence"
    )

    assert response.status_code == 200

    evidence = (
        response.json()[
            "evidence"
        ]
    )

    evidence_ids = [
        row["evidence_id"]
        for row in evidence
    ]

    assert (
        len(evidence_ids)
        ==
        len(set(evidence_ids))
    )


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