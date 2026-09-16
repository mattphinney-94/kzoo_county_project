from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.database import engine
from api.schemas import AssociationEvidenceResponse


# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter(
    prefix="/api/associations",
    tags=["Associations"]
)


# ==========================================================
# ASSOCIATION EVIDENCE
# ==========================================================

@router.get(
    "/{association_id}/evidence",
    response_model=AssociationEvidenceResponse
)
def get_association_evidence(
        association_id: int
):
    """
    Return the individual pieces of evidence supporting
    one entity association.

    Association confidence represents the strongest
    individual evidence rule and should not be interpreted
    as a probability of ownership or control.
    """

    association_query = text(
        """
        SELECT
            a.association_id,

            a.entity_id_a,
            entity_a.canonical_name
                AS entity_name_a,
            entity_a.entity_type
                AS entity_type_a,

            a.entity_id_b,
            entity_b.canonical_name
                AS entity_name_b,
            entity_b.entity_type
                AS entity_type_b,

            a.association_confidence,
            a.evidence_count,
            a.evidence_rule_count

        FROM entity_associations a

        JOIN entities entity_a
            ON entity_a.entity_id
                = a.entity_id_a

        JOIN entities entity_b
            ON entity_b.entity_id
                = a.entity_id_b

        WHERE a.association_id = :association_id
        """
    )

    evidence_query = text(
        """
        SELECT
            evidence_id,
            evidence_rule,
            evidence_strength,
            parcel_number_a,
            parcel_number_b,
            role_a,
            role_b,
            shared_address,
            address_type

        FROM association_evidence

        WHERE
            entity_id_a = :entity_id_a
            AND entity_id_b = :entity_id_b

        ORDER BY
            CASE evidence_strength
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,

            evidence_rule,
            parcel_number_a,
            parcel_number_b,
            evidence_id
        """
    )

    try:
        with engine.connect() as connection:

            association = (
                connection.execute(
                    association_query,
                    {
                        "association_id":
                            association_id
                    }
                )
                .mappings()
                .first()
            )

            if association is None:
                raise HTTPException(
                    status_code=404,
                    detail="Association not found."
                )

            evidence_rows = (
                connection.execute(
                    evidence_query,
                    {
                        "entity_id_a":
                            association[
                                "entity_id_a"
                            ],

                        "entity_id_b":
                            association[
                                "entity_id_b"
                            ]
                    }
                )
                .mappings()
                .all()
            )

    except HTTPException:
        raise

    except SQLAlchemyError:

        raise HTTPException(
            status_code=503,
            detail="Database query failed."
        )

    evidence = [
        dict(row)
        for row in evidence_rows
    ]

    return {
        "association_id":
            association[
                "association_id"
            ],

        "entity_a": {
            "entity_id":
                association[
                    "entity_id_a"
                ],

            "canonical_name":
                association[
                    "entity_name_a"
                ],

            "entity_type":
                association[
                    "entity_type_a"
                ]
        },

        "entity_b": {
            "entity_id":
                association[
                    "entity_id_b"
                ],

            "canonical_name":
                association[
                    "entity_name_b"
                ],

            "entity_type":
                association[
                    "entity_type_b"
                ]
        },

        "association_confidence":
            association[
                "association_confidence"
            ],

        "evidence_count":
            association[
                "evidence_count"
            ],

        "evidence_rule_count":
            association[
                "evidence_rule_count"
            ],

        "evidence":
            evidence
    }