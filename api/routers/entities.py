from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.database import (
    engine,
    get_active_snapshot_id
)
from api.schemas import (
    EntityAssociationsResponse,
    EntityDetailResponse,
    EntityParcelsResponse,
    EntitySearchResponse
)

import logging
logger = logging.getLogger(__name__)


# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter(
    prefix="/api/entities",
    tags=["Entities"]
)


# ==========================================================
# ENTITY SEARCH
# ==========================================================

@router.get(
    "/search",
    response_model=EntitySearchResponse
)
def search_entities(
        q: str = Query(
            ...,
            min_length=1,
            max_length=100,
            description="Name or partial name to search for."
        ),
        limit: int = Query(
            25,
            ge=1,
            le=100,
            description="Maximum number of entities to return."
        )
):
    """
    Search resolved entities by canonical name or by any
    original source name that resolved to the entity.

    Searching source_entity_name allows source spelling
    variants to remain discoverable even when the entity has
    a different canonical name.
    """

    search_term = q.strip()

    if not search_term:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be blank."
        )

    normalized_term = search_term.lower()

    escaped_term = (
        normalized_term
        .replace(
            "!",
            "!!"
        )
        .replace(
            "%",
            "!%"
        )
        .replace(
            "_",
            "!_"
        )
    )

    contains_pattern = (
        f"%{escaped_term}%"
    )

    prefix_pattern = (
        f"{escaped_term}%"
    )

    search_query = text(
        """
        SELECT
            e.entity_id,
            e.canonical_name,
            e.entity_type,
            e.canonical_address,
            e.organization_type,
            e.organization_classification_confidence,
            e.occurrence_count

        FROM entities e

        WHERE
            LOWER(e.canonical_name) LIKE :contains_pattern ESCAPE '!'

            OR EXISTS (
                SELECT 1
                FROM entity_occurrences eo
                WHERE
                    eo.entity_id = e.entity_id
                    AND LOWER(eo.source_entity_name)
                        LIKE :contains_pattern ESCAPE '!'
            )

        ORDER BY
            CASE

                -- Exact canonical-name match
                WHEN LOWER(e.canonical_name)
                    = :normalized_term
                THEN 0

                -- Canonical name begins with search term
                WHEN LOWER(e.canonical_name)
                    LIKE :prefix_pattern ESCAPE '!'
                THEN 1

                -- Exact original source-name match
                WHEN EXISTS (
                    SELECT 1
                    FROM entity_occurrences eo
                    WHERE
                        eo.entity_id = e.entity_id
                        AND LOWER(eo.source_entity_name)
                            = :normalized_term
                )
                THEN 2

                -- Original source name begins with search term
                WHEN EXISTS (
                    SELECT 1
                    FROM entity_occurrences eo
                    WHERE
                        eo.entity_id = e.entity_id
                        AND LOWER(eo.source_entity_name)
                            LIKE :prefix_pattern ESCAPE '!'
                )
                THEN 3

                -- Other substring match
                ELSE 4

            END,

            e.canonical_name,
            e.entity_id

        LIMIT :limit
        """
    )

    try:
        with engine.connect() as connection:

            rows = (
                connection.execute(
                    search_query,
                    {
                        "contains_pattern":
                            contains_pattern,

                        "prefix_pattern":
                            prefix_pattern,

                        "normalized_term":
                            normalized_term,

                        "limit":
                            limit
                    }
                )
                .mappings()
                .all()
            )

    except SQLAlchemyError:
        logger.exception(
            "Database query failed."
        )
        raise HTTPException(
            status_code=503,
            detail="Database query failed."
        )

    results = [
        dict(row)
        for row in rows
    ]

    return {
        "query": search_term,
        "result_count": len(results),
        "results": results
    }

# ==========================================================
# ENTITY DETAIL
# ==========================================================

@router.get(
    "/{entity_id}",
    response_model=EntityDetailResponse
)
def get_entity(
        entity_id: int
):
    """
    Return one resolved entity by entity_id.
    """

    entity_query = text(
        """
        SELECT
            entity_id,
            canonical_name,
            entity_type,
            canonical_address,
            organization_type,
            organization_classification_confidence,
            occurrence_count

        FROM entities

        WHERE entity_id = :entity_id
        """
    )

    try:
        with engine.connect() as connection:

            row = (
                connection.execute(
                    entity_query,
                    {
                        "entity_id":
                            entity_id
                    }
                )
                .mappings()
                .first()
            )

    except SQLAlchemyError:
        logger.exception(
            "Database query failed."
        )
        raise HTTPException(
            status_code=503,
            detail="Database query failed."
        )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Entity not found."
        )

    return dict(row)

# ==========================================================
# ENTITY PARCELS
# ==========================================================

@router.get(
    "/{entity_id}/parcels",
    response_model=EntityParcelsResponse
)
def get_entity_parcels(
        entity_id: int
):
    """
    Return all parcels directly associated with an entity,
    along with the entity's role or roles on each parcel.
    """

    entity_exists_query = text(
        """
        SELECT 1
        FROM entities
        WHERE entity_id = :entity_id
        """
    )

    parcel_query = text(
        """
        SELECT
            p.parcel_number,
            p.property_address,
            per.role,
            p.principal_residence_exemption_percentage,
            p.property_class,
            p.tax_value,
            p.assessed_value,
            p.state_equalized_value

        FROM parcel_entity_roles per

        JOIN parcels p
            ON p.parcel_number = per.parcel_number

        WHERE per.entity_id = :entity_id

        ORDER BY
            p.parcel_number,
            per.role
        """
    )

    try:
        with engine.connect() as connection:

            entity_exists = (
                connection.execute(
                    entity_exists_query,
                    {
                        "entity_id": entity_id
                    }
                )
                .first()
                is not None
            )

            if not entity_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Entity not found."
                )

            rows = (
                connection.execute(
                    parcel_query,
                    {
                        "entity_id": entity_id
                    }
                )
                .mappings()
                .all()
            )

    except HTTPException:
        raise

    except SQLAlchemyError:
        logger.exception(
            "Database query failed."
        )
        raise HTTPException(
            status_code=503,
            detail="Database query failed."
        )

    parcels_by_number = {}

    for row in rows:

        parcel_number = row[
            "parcel_number"
        ]

        if parcel_number not in parcels_by_number:

            parcels_by_number[
                parcel_number
            ] = {
                "parcel_number":
                    parcel_number,

                "property_address":
                    row["property_address"],

                "roles": [],

                "principal_residence_exemption_percentage":
                    row[
                        "principal_residence_exemption_percentage"
                    ],

                "property_class":
                    row["property_class"],

                "tax_value":
                    row["tax_value"],

                "assessed_value":
                    row["assessed_value"],

                "state_equalized_value":
                    row["state_equalized_value"]
            }

        parcels_by_number[
            parcel_number
        ][
            "roles"
        ].append(
            row["role"]
        )

    parcels = list(
        parcels_by_number.values()
    )

    return {
        "entity_id": entity_id,
        "parcel_count": len(parcels),
        "parcels": parcels
    }

# ==========================================================
# ENTITY ASSOCIATIONS
# ==========================================================

@router.get(
    "/{entity_id}/associations",
    response_model=EntityAssociationsResponse
)
def get_entity_associations(
        entity_id: int
):
    """
    Return entities associated with the requested entity.

    Associations are ordered by confidence from High to Low,
    followed by evidence count and entity name.

    Association confidence represents the strongest individual
    evidence rule supporting the association. Evidence counts
    provide additional context but do not independently increase
    the confidence level.
    """

    entity_exists_query = text(
        """
        SELECT 1
        FROM entities
        WHERE entity_id = :entity_id
        """
    )

    associations_query = text(
        """
        SELECT n.association_id,

               associated.entity_id
                   AS associated_entity_id,

               associated.canonical_name
                   AS associated_canonical_name,

               associated.entity_type
                   AS associated_entity_type,

               associated.canonical_address
                   AS associated_canonical_address,

               associated.organization_type
                   AS associated_organization_type,

               associated.organization_classification_confidence
                   AS associated_organization_classification_confidence,

               n.association_confidence,
               n.evidence_count,
               n.evidence_rule_count

        FROM entity_association_neighbors n

                 JOIN entities associated
                      ON associated.entity_id
                          = n.associated_entity_id

        WHERE n.entity_id = :entity_id

                    AND NOT EXISTS (
              SELECT 1

              FROM association_suppressions suppression

              WHERE suppression.snapshot_id
                    = :active_snapshot_id

                AND suppression.association_id
                    = n.association_id

                AND suppression.revoked_at IS NULL
          )

        ORDER BY CASE n.association_confidence
                     WHEN 'High' THEN 1
                     WHEN 'Medium' THEN 2
                     WHEN 'Low' THEN 3
                     ELSE 4
                     END,
                 n.evidence_count DESC,
                 n.evidence_rule_count DESC,
                 associated.canonical_name,
                 associated.entity_id
        """
    )

    try:
        with engine.connect() as connection:

            active_snapshot_id = (
                get_active_snapshot_id(
                    connection
                )
            )

            if active_snapshot_id is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "No active data snapshot "
                        "is configured."
                    )
                )

            entity_exists = (
                connection.execute(
                    entity_exists_query,
                    {
                        "entity_id":
                            entity_id
                    }
                )
                .first()
                is not None
            )

            if not entity_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Entity not found."
                )

            rows = (
                connection.execute(
                    associations_query,
                    {
                        "entity_id":
                            entity_id,

                        "active_snapshot_id":
                            active_snapshot_id
                    }
                )
                .mappings()
                .all()
            )

    except HTTPException:
        raise

    except SQLAlchemyError:
        logger.exception(
            "Database query failed."
        )
        raise HTTPException(
            status_code=503,
            detail="Database query failed."
        )

    associations = [
        dict(row)
        for row in rows
    ]

    return {
        "entity_id":
            entity_id,

        "association_count":
            len(associations),

        "associations":
            associations
    }