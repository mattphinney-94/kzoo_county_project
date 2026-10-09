from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

from api.admin_database import (
    admin_engine as real_admin_engine
)
from api.database import engine as read_engine
import api.routers.admin as admin_router


# ==========================================================
# TEST DATABASE HELPERS
# ==========================================================

class RollbackAdminEngine:
    """
    Wrapper around the real administrative SQLAlchemy engine.

    Every transaction opened through begin() is rolled back
    instead of committed. This allows the admin API to execute
    real INSERT statements without leaving test suppressions
    in the database.
    """

    def __init__(self, engine):
        self.engine = engine

    @contextmanager
    def begin(self):

        connection = self.engine.connect()
        transaction = connection.begin()

        try:
            yield connection

        finally:
            transaction.rollback()
            connection.close()

class SharedTransactionAdminEngine:
    """
    Allow multiple admin API calls to use the same database
    transaction during one integration test.
    """

    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection

@contextmanager
def shared_admin_test_transaction(
        monkeypatch
):
    """
    Run multiple admin API requests inside one transaction
    and roll the entire sequence back afterward.
    """

    connection = real_admin_engine.connect()
    transaction = connection.begin()

    original_engine = (
        admin_router.admin_engine
    )

    shared_engine = SharedTransactionAdminEngine(
        connection
    )

    monkeypatch.setattr(
        admin_router,
        "admin_engine",
        shared_engine
    )

    try:
        yield connection

    finally:

        transaction.rollback()
        connection.close()

        monkeypatch.setattr(
            admin_router,
            "admin_engine",
            original_engine
        )


@pytest.fixture
def rollback_admin_writes(
        monkeypatch
):
    """
    Replace the admin router's database engine with an engine
    that rolls back every administrative transaction.
    """

    rollback_engine = RollbackAdminEngine(
        real_admin_engine
    )

    monkeypatch.setattr(
        admin_router,
        "admin_engine",
        rollback_engine
    )


def get_test_association_id():
    """
    Retrieve an existing association that is not currently
    suppressed for the active snapshot.
    """

    query = text(
        """
        SELECT
            a.association_id

        FROM entity_associations a

        JOIN active_data_snapshot active_snapshot
            ON active_snapshot.singleton_id = 1

        WHERE NOT EXISTS (
            SELECT 1

            FROM association_suppressions suppression

            WHERE
                suppression.snapshot_id
                    = active_snapshot.snapshot_id

                AND suppression.association_id
                    = a.association_id

                AND suppression.revoked_at IS NULL
        )

        ORDER BY a.association_id

        LIMIT 1
        """
    )

    with read_engine.connect() as connection:

        association_id = (
            connection.execute(
                query
            )
            .scalar_one_or_none()
        )

    if association_id is None:
        pytest.fail(
            "No unsuppressed entity association is "
            "available for administrative API testing."
        )

    return association_id

def get_active_snapshot():
    """
    Retrieve metadata for the currently active data snapshot.
    """

    query = text(
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

    with read_engine.connect() as connection:

        snapshot = (
            connection.execute(
                query
            )
            .mappings()
            .first()
        )

    if snapshot is None:
        pytest.fail(
            "No active data snapshot is available "
            "for administrative API testing."
        )

    return dict(snapshot)


# ==========================================================
# AUTHENTICATION
# ==========================================================

def test_suppression_requires_admin_key(
        client
):

    association_id = get_test_association_id()

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/suppress"
        ),
        json={
            "reason":
                "Administrative API test.",

            "created_by":
                "pytest"
        }
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail":
            "Invalid or missing admin API key."
    }


def test_suppression_rejects_invalid_admin_key(
        client
):

    association_id = get_test_association_id()

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/suppress"
        ),
        headers={
            "X-Admin-Key":
                "definitely-not-the-real-key"
        },
        json={
            "reason":
                "Administrative API test.",

            "created_by":
                "pytest"
        }
    )

    assert response.status_code == 401

@pytest.mark.parametrize(
    (
        "method",
        "path",
        "request_body"
    ),
    [
        (
            "post",
            "/api/admin/associations/1/suppress",
            {
                "reason":
                    "Administrative API test.",

                "created_by":
                    "pytest"
            }
        ),
        (
            "post",
            "/api/admin/associations/1/restore",
            {
                "revoked_by":
                    "pytest",

                "revocation_reason":
                    "Administrative API test."
            }
        ),
        (
            "get",
            "/api/admin/association-suppressions",
            None
        )
    ]
)
def test_admin_endpoints_require_active_snapshot(
        client,
        admin_headers,
        monkeypatch,
        method,
        path,
        request_body
):
    """
    Administrative association operations must fail closed
    when no active data snapshot is configured.
    """

    result = MagicMock()

    result.scalar_one_or_none.return_value = None

    result.mappings.return_value.first.return_value = (
        None
    )

    mock_connection = MagicMock()

    mock_connection.execute.return_value = (
        result
    )

    mock_engine = MagicMock()

    mock_engine.begin.return_value.__enter__.return_value = (
        mock_connection
    )

    mock_engine.connect.return_value.__enter__.return_value = (
        mock_connection
    )

    monkeypatch.setattr(
        admin_router,
        "admin_engine",
        mock_engine
    )

    request_kwargs = {
        "headers":
            admin_headers
    }

    if request_body is not None:
        request_kwargs[
            "json"
        ] = request_body

    response = getattr(
        client,
        method
    )(
        path,
        **request_kwargs
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail":
            "No active data snapshot is configured."
    }

# ==========================================================
# INPUT VALIDATION
# ==========================================================

def test_suppression_rejects_blank_reason(
        client,
        admin_headers
):

    association_id = get_test_association_id()

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/suppress"
        ),
        headers=admin_headers,
        json={
            "reason": "   ",
            "created_by": "pytest"
        }
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail":
            "Suppression reason cannot be blank."
    }


def test_suppression_rejects_blank_created_by(
        client,
        admin_headers
):

    association_id = get_test_association_id()

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/suppress"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Administrative API test.",

            "created_by":
                "   "
        }
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail":
            "created_by cannot be blank."
    }


def test_suppression_rejects_excessive_reason_length(
        client,
        admin_headers
):

    association_id = get_test_association_id()

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/suppress"
        ),
        headers=admin_headers,
        json={
            "reason": "A" * 1001,
            "created_by": "pytest"
        }
    )

    assert response.status_code == 422


# ==========================================================
# RESOURCE VALIDATION
# ==========================================================

def test_suppression_nonexistent_association_returns_404(
        client,
        admin_headers,
        rollback_admin_writes
):

    response = client.post(
        "/api/admin/associations/99999999/suppress",
        headers=admin_headers,
        json={
            "reason":
                "Administrative API test.",

            "created_by":
                "pytest"
        }
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail":
            "Association not found."
    }


# ==========================================================
# SUCCESSFUL SUPPRESSION
# ==========================================================

def test_association_can_be_suppressed(
        client,
        admin_headers,
        rollback_admin_writes
):

    association_id = get_test_association_id()
    active_snapshot = get_active_snapshot()

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/suppress"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Automated integration test. "
                "This transaction will be rolled back.",

            "created_by":
                "pytest"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert (
        data["association_id"]
        ==
        association_id
    )

    assert (
            data["snapshot_id"]
            ==
            active_snapshot["snapshot_id"]
    )

    assert data["suppression_id"] > 0

    assert data["entity_id_a"] > 0
    assert data["entity_id_b"] > 0

    assert data["entity_name_a"]
    assert data["entity_name_b"]

    assert (
        data["reason"]
        ==
        "Automated integration test. "
        "This transaction will be rolled back."
    )

    assert data["created_by"] == "pytest"


def test_suppression_test_does_not_persist(
        client,
        admin_headers,
        rollback_admin_writes
):

    association_id = get_test_association_id()

    test_reason = (
        "Rollback verification suppression."
    )

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/suppress"
        ),
        headers=admin_headers,
        json={
            "reason": test_reason,
            "created_by": "pytest"
        }
    )

    assert response.status_code == 201

    verification_query = text(
        """
        SELECT COUNT(*)

        FROM association_suppressions

        WHERE
            association_id = :association_id
            AND reason = :reason
        """
    )

    with read_engine.connect() as connection:

        persisted_count = (
            connection.execute(
                verification_query,
                {
                    "association_id":
                        association_id,

                    "reason":
                        test_reason
                }
            )
            .scalar_one()
        )

    assert persisted_count == 0

# ==========================================================
# RESTORE SUPPRESSION
# ==========================================================

def test_restore_requires_admin_key(
        client
):

    association_id = get_test_association_id()

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/restore"
        ),
        json={
            "revoked_by": "pytest",
            "revocation_reason":
                "Administrative API test."
        }
    )

    assert response.status_code == 401


def test_restore_nonexistent_association_returns_404(
        client,
        admin_headers,
        rollback_admin_writes
):

    response = client.post(
        "/api/admin/associations/99999999/restore",
        headers=admin_headers,
        json={
            "revoked_by": "pytest",
            "revocation_reason":
                "Administrative API test."
        }
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail":
            "Association not found."
    }


def test_restore_unsuppressed_association_returns_409(
        client,
        admin_headers,
        rollback_admin_writes
):

    association_id = get_test_association_id()

    response = client.post(
        (
            f"/api/admin/associations/"
            f"{association_id}/restore"
        ),
        headers=admin_headers,
        json={
            "revoked_by": "pytest",
            "revocation_reason":
                "Administrative API test."
        }
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail":
            "Association is not currently "
            "suppressed for the active snapshot."
    }


def test_association_can_be_suppressed_and_restored(
        client,
        admin_headers,
        monkeypatch
):

    association_id = get_test_association_id()

    suppression_reason = (
        "Temporary suppression for restore test."
    )

    with shared_admin_test_transaction(
        monkeypatch
    ) as connection:

        suppress_response = client.post(
            (
                f"/api/admin/associations/"
                f"{association_id}/suppress"
            ),
            headers=admin_headers,
            json={
                "reason":
                    suppression_reason,

                "created_by":
                    "pytest"
            }
        )

        assert (
            suppress_response.status_code
            ==
            201
        )

        suppression_id = (
            suppress_response.json()[
                "suppression_id"
            ]
        )

        restore_response = client.post(
            (
                f"/api/admin/associations/"
                f"{association_id}/restore"
            ),
            headers=admin_headers,
            json={
                "revoked_by":
                    "pytest",

                "revocation_reason":
                    "Restore integration test."
            }
        )

        assert (
            restore_response.status_code
            ==
            200
        )

        data = restore_response.json()

        assert (
            data["suppression_id"]
            ==
            suppression_id
        )

        assert (
            data["association_id"]
            ==
            association_id
        )

        assert data["revoked_by"] == "pytest"

        assert (
            data["revocation_reason"]
            ==
            "Restore integration test."
        )

        assert data["revoked_at"] is not None

        verification_query = text(
            """
            SELECT
                revoked_at,
                revoked_by,
                revocation_reason

            FROM association_suppressions

            WHERE suppression_id = :suppression_id
            """
        )

        restored_row = (
            connection.execute(
                verification_query,
                {
                    "suppression_id":
                        suppression_id
                }
            )
            .mappings()
            .one()
        )

        assert (
            restored_row["revoked_at"]
            is not None
        )

        assert (
            restored_row["revoked_by"]
            ==
            "pytest"
        )

        assert (
            restored_row[
                "revocation_reason"
            ]
            ==
            "Restore integration test."
        )

    # The enclosing test transaction has now rolled back.
    persisted_query = text(
        """
        SELECT COUNT(*)

        FROM association_suppressions

        WHERE
            association_id = :association_id
            AND reason = :reason
        """
    )

    with read_engine.connect() as connection:

        persisted_count = (
            connection.execute(
                persisted_query,
                {
                    "association_id":
                        association_id,

                    "reason":
                        suppression_reason
                }
            )
            .scalar_one()
        )

    assert persisted_count == 0

# ==========================================================
# LIST SUPPRESSIONS
# ==========================================================

def test_suppression_list_requires_admin_key(
        client
):

    response = client.get(
        "/api/admin/association-suppressions"
    )

    assert response.status_code == 401


def test_active_suppression_appears_in_admin_list(
        client,
        admin_headers,
        monkeypatch
):

    association_id = get_test_association_id()
    active_snapshot = get_active_snapshot()

    test_reason = (
        "Temporary suppression for admin list test."
    )

    with shared_admin_test_transaction(
        monkeypatch
    ):

        suppress_response = client.post(
            (
                f"/api/admin/associations/"
                f"{association_id}/suppress"
            ),
            headers=admin_headers,
            json={
                "reason":
                    test_reason,

                "created_by":
                    "pytest"
            }
        )

        assert (
            suppress_response.status_code
            ==
            201
        )

        suppression_id = (
            suppress_response.json()[
                "suppression_id"
            ]
        )

        list_response = client.get(
            "/api/admin/association-suppressions",
            headers=admin_headers
        )

        assert list_response.status_code == 200

        data = list_response.json()

        assert (
                data["snapshot_id"]
                ==
                active_snapshot["snapshot_id"]
        )

        assert (
                data["snapshot_code"]
                ==
                active_snapshot["snapshot_code"]
        )

        assert (
                data["tax_year"]
                ==
                active_snapshot["tax_year"]
        )

        assert (
            data["include_restored"]
            is False
        )

        matching_records = [
            record
            for record in data[
                "suppressions"
            ]
            if record["suppression_id"]
            == suppression_id
        ]

        assert len(matching_records) == 1

        record = matching_records[0]

        assert (
            record["association_id"]
            ==
            association_id
        )

        assert record["is_active"] is True
        assert record["revoked_at"] is None
        assert record["reason"] == test_reason


def test_restored_suppression_only_appears_when_requested(
        client,
        admin_headers,
        monkeypatch
):

    association_id = get_test_association_id()

    with shared_admin_test_transaction(
        monkeypatch
    ):

        suppress_response = client.post(
            (
                f"/api/admin/associations/"
                f"{association_id}/suppress"
            ),
            headers=admin_headers,
            json={
                "reason":
                    "Temporary suppression "
                    "for history test.",

                "created_by":
                    "pytest"
            }
        )

        assert (
            suppress_response.status_code
            ==
            201
        )

        suppression_id = (
            suppress_response.json()[
                "suppression_id"
            ]
        )

        restore_response = client.post(
            (
                f"/api/admin/associations/"
                f"{association_id}/restore"
            ),
            headers=admin_headers,
            json={
                "revoked_by":
                    "pytest",

                "revocation_reason":
                    "Restore for admin "
                    "history test."
            }
        )

        assert (
            restore_response.status_code
            ==
            200
        )

        active_only_response = client.get(
            "/api/admin/association-suppressions",
            headers=admin_headers
        )

        assert (
            active_only_response.status_code
            ==
            200
        )

        active_ids = {
            record["suppression_id"]
            for record
            in active_only_response.json()[
                "suppressions"
            ]
        }

        assert suppression_id not in active_ids

        history_response = client.get(
            (
                "/api/admin/"
                "association-suppressions"
                "?include_restored=true"
            ),
            headers=admin_headers
        )

        assert history_response.status_code == 200

        history_records = [
            record
            for record
            in history_response.json()[
                "suppressions"
            ]
            if record["suppression_id"]
            == suppression_id
        ]

        assert len(history_records) == 1

        record = history_records[0]

        assert record["is_active"] is False
        assert record["revoked_at"] is not None
        assert record["revoked_by"] == "pytest"

        assert (
            record["revocation_reason"]
            ==
            "Restore for admin history test."
        )

