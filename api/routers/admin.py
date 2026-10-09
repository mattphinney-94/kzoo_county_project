from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy import text
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError
)

from api.admin_database import admin_engine
from api.auth import require_admin_api_key
from api.schemas import (
    AssociationSuppressionRequest,
    AssociationSuppressionResponse,
    AssociationSuppressionRestoreRequest,
    AssociationSuppressionRestoreResponse,
    AssociationSuppressionRecord,
    AssociationSuppressionListResponse
)

import logging
logger = logging.getLogger(__name__)


# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter(
    prefix="/api/admin",
    tags=["Administration"],
    dependencies=[
        Depends(require_admin_api_key)
    ]
)


# ==========================================================
# SUPPRESS ASSOCIATION
# ==========================================================

@router.post(
    "/associations/{association_id}/suppress",
    response_model=AssociationSuppressionResponse,
    status_code=201
)
def suppress_association(
        association_id: int,
        request: AssociationSuppressionRequest
):
    """
    Suppress one generated entity association for the
    currently active data snapshot.

    The generated association and its evidence remain
    unchanged. The suppression affects API presentation only.
    """

    reason = request.reason.strip()
    created_by = request.created_by.strip()

    if not reason:
        raise HTTPException(
            status_code=400,
            detail="Suppression reason cannot be blank."
        )

    if not created_by:
        raise HTTPException(
            status_code=400,
            detail="created_by cannot be blank."
        )

    active_snapshot_query = text(
        """
        SELECT
            snapshot_id

        FROM active_data_snapshot

        WHERE singleton_id = 1
        """
    )

    association_query = text(
        """
        SELECT
            a.association_id,

            a.entity_id_a,
            entity_a.canonical_name
                AS entity_name_a,

            a.entity_id_b,
            entity_b.canonical_name
                AS entity_name_b

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

    existing_suppression_query = text(
        """
        SELECT
            suppression_id

        FROM association_suppressions

        WHERE
            snapshot_id = :snapshot_id
            AND association_id = :association_id
            AND revoked_at IS NULL
        """
    )

    insert_suppression_query = text(
        """
        INSERT INTO association_suppressions (
            snapshot_id,
            association_id,

            entity_id_a,
            entity_id_b,

            entity_name_a,
            entity_name_b,

            reason,
            created_by
        )
        VALUES (
            :snapshot_id,
            :association_id,

            :entity_id_a,
            :entity_id_b,

            :entity_name_a,
            :entity_name_b,

            :reason,
            :created_by
        )
        """
    )

    try:

        with admin_engine.begin() as connection:

            snapshot_id = (
                connection.execute(
                    active_snapshot_query
                )
                .scalar_one_or_none()
            )

            if snapshot_id is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "No active data snapshot "
                        "is configured."
                    )
                )

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

            existing_suppression = (
                connection.execute(
                    existing_suppression_query,
                    {
                        "snapshot_id":
                            snapshot_id,

                        "association_id":
                            association_id
                    }
                )
                .scalar_one_or_none()
            )

            if existing_suppression is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Association is already "
                        "suppressed for the active snapshot."
                    )
                )

            result = connection.execute(
                insert_suppression_query,
                {
                    "snapshot_id":
                        snapshot_id,

                    "association_id":
                        association_id,

                    "entity_id_a":
                        association[
                            "entity_id_a"
                        ],

                    "entity_id_b":
                        association[
                            "entity_id_b"
                        ],

                    "entity_name_a":
                        association[
                            "entity_name_a"
                        ],

                    "entity_name_b":
                        association[
                            "entity_name_b"
                        ],

                    "reason":
                        reason,

                    "created_by":
                        created_by
                }
            )

            suppression_id = (
                result.lastrowid
            )

    except HTTPException:
        raise


    except IntegrityError:

        logger.exception(

            "Integrity error while suppressing association."

        )

        raise HTTPException(

            status_code=409,

            detail=(

                "Association suppression could "

                "not be created because an active "

                "suppression already exists."

            )

        )


    except SQLAlchemyError:

        logger.exception(

            "Database operation failed while "

            "suppressing association."

        )

        raise HTTPException(

            status_code=503,

            detail="Database operation failed."

        )

    return {
        "suppression_id":
            suppression_id,

        "snapshot_id":
            snapshot_id,

        "association_id":
            association_id,

        "entity_id_a":
            association[
                "entity_id_a"
            ],

        "entity_name_a":
            association[
                "entity_name_a"
            ],

        "entity_id_b":
            association[
                "entity_id_b"
            ],

        "entity_name_b":
            association[
                "entity_name_b"
            ],

        "reason":
            reason,

        "created_by":
            created_by
    }

# ==========================================================
# RESTORE ASSOCIATION
# ==========================================================

@router.post(
    "/associations/{association_id}/restore",
    response_model=AssociationSuppressionRestoreResponse
)
def restore_association(
        association_id: int,
        request: AssociationSuppressionRestoreRequest
):
    """
    Restore an association by revoking its active suppression
    for the currently active data snapshot.

    The suppression record is retained for audit history.
    """

    revoked_by = request.revoked_by.strip()
    revocation_reason = (
        request.revocation_reason.strip()
    )

    if not revoked_by:
        raise HTTPException(
            status_code=400,
            detail="revoked_by cannot be blank."
        )

    if not revocation_reason:
        raise HTTPException(
            status_code=400,
            detail="Revocation reason cannot be blank."
        )

    active_snapshot_query = text(
        """
        SELECT
            snapshot_id

        FROM active_data_snapshot

        WHERE singleton_id = 1
        """
    )

    association_exists_query = text(
        """
        SELECT
            association_id

        FROM entity_associations

        WHERE association_id = :association_id
        """
    )

    active_suppression_query = text(
        """
        SELECT
            suppression_id,
            snapshot_id,
            association_id,

            entity_id_a,
            entity_name_a,

            entity_id_b,
            entity_name_b

        FROM association_suppressions

        WHERE
            snapshot_id = :snapshot_id
            AND association_id = :association_id
            AND revoked_at IS NULL

        FOR UPDATE
        """
    )

    restore_query = text(
        """
        UPDATE association_suppressions

        SET
            revoked_at = CURRENT_TIMESTAMP(6),
            revoked_by = :revoked_by,
            revocation_reason = :revocation_reason

        WHERE
            suppression_id = :suppression_id
            AND revoked_at IS NULL
        """
    )

    restored_suppression_query = text(
        """
        SELECT
            suppression_id,
            snapshot_id,
            association_id,

            entity_id_a,
            entity_name_a,

            entity_id_b,
            entity_name_b,

            revoked_at,
            revoked_by,
            revocation_reason

        FROM association_suppressions

        WHERE suppression_id = :suppression_id
        """
    )

    try:

        with admin_engine.begin() as connection:

            snapshot_id = (
                connection.execute(
                    active_snapshot_query
                )
                .scalar_one_or_none()
            )

            if snapshot_id is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "No active data snapshot "
                        "is configured."
                    )
                )

            association_exists = (
                connection.execute(
                    association_exists_query,
                    {
                        "association_id":
                            association_id
                    }
                )
                .scalar_one_or_none()
            )

            if association_exists is None:
                raise HTTPException(
                    status_code=404,
                    detail="Association not found."
                )

            suppression = (
                connection.execute(
                    active_suppression_query,
                    {
                        "snapshot_id":
                            snapshot_id,

                        "association_id":
                            association_id
                    }
                )
                .mappings()
                .first()
            )

            if suppression is None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Association is not currently "
                        "suppressed for the active snapshot."
                    )
                )

            result = connection.execute(
                restore_query,
                {
                    "suppression_id":
                        suppression[
                            "suppression_id"
                        ],

                    "revoked_by":
                        revoked_by,

                    "revocation_reason":
                        revocation_reason
                }
            )

            if result.rowcount != 1:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Association suppression could "
                        "not be restored."
                    )
                )

            restored_suppression = (
                connection.execute(
                    restored_suppression_query,
                    {
                        "suppression_id":
                            suppression[
                                "suppression_id"
                            ]
                    }
                )
                .mappings()
                .one()
            )

    except HTTPException:
        raise

    except SQLAlchemyError:

        logger.exception(

            "Database operation failed while "

            "restoring association."

        )

        raise HTTPException(

            status_code=503,

            detail="Database operation failed."

        )

    return dict(
        restored_suppression
    )

# ==========================================================
# LIST ASSOCIATION SUPPRESSIONS
# ==========================================================

@router.get(
    "/association-suppressions",
    response_model=AssociationSuppressionListResponse
)
def list_association_suppressions(
        include_restored: bool = False
):
    """
    Return association suppressions for the currently active
    data snapshot.

    By default, only active suppressions are returned.
    Set include_restored=true to include suppression records
    that were later revoked.
    """

    active_snapshot_query = text(
        """
        SELECT
            ds.snapshot_id,
            ds.snapshot_code,
            ds.tax_year

        FROM active_data_snapshot ads

        JOIN data_snapshots ds
            ON ds.snapshot_id
                = ads.snapshot_id

        WHERE ads.singleton_id = 1
        """
    )

    suppressions_query = text(
        """
        SELECT
            suppression_id,
            snapshot_id,
            association_id,

            entity_id_a,
            entity_name_a,

            entity_id_b,
            entity_name_b,

            reason,
            created_at,
            created_by,

            revoked_at,
            revoked_by,
            revocation_reason,

            CASE
                WHEN revoked_at IS NULL
                    THEN TRUE
                ELSE FALSE
            END AS is_active

        FROM association_suppressions

        WHERE
            snapshot_id = :snapshot_id

            AND (
                :include_restored = 1
                OR revoked_at IS NULL
            )

        ORDER BY
            CASE
                WHEN revoked_at IS NULL
                    THEN 0
                ELSE 1
            END,

            created_at DESC,
            suppression_id DESC
        """
    )

    try:

        with admin_engine.connect() as connection:

            snapshot = (
                connection.execute(
                    active_snapshot_query
                )
                .mappings()
                .first()
            )

            if snapshot is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "No active data snapshot "
                        "is configured."
                    )
                )

            suppressions = (
                connection.execute(
                    suppressions_query,
                    {
                        "snapshot_id":
                            snapshot[
                                "snapshot_id"
                            ],

                        "include_restored":
                            1
                            if include_restored
                            else 0
                    }
                )
                .mappings()
                .all()
            )

    except HTTPException:
        raise

    except SQLAlchemyError:

        logger.exception(

            "Database operation failed while listing "

            "association suppressions."

        )

        raise HTTPException(

            status_code=503,

            detail="Database operation failed."

        )

    suppression_records = [
        {
            **dict(row),
            "is_active":
                bool(row["is_active"])
        }
        for row in suppressions
    ]

    return {
        "snapshot_id":
            snapshot["snapshot_id"],

        "snapshot_code":
            snapshot["snapshot_code"],

        "tax_year":
            snapshot["tax_year"],

        "include_restored":
            include_restored,

        "count":
            len(suppression_records),

        "suppressions":
            suppression_records
    }