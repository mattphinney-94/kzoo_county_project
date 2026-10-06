from unittest.mock import MagicMock

import pytest

from database.load_database import (
    _register_and_activate_snapshot
)


def _make_scalar_result(value):
    """
    Create a mock SQLAlchemy result whose
    scalar_one_or_none() method returns value.
    """

    result = MagicMock()

    result.scalar_one_or_none.return_value = value

    return result


def test_register_and_activate_snapshot_success():
    """
    A valid new snapshot should be inserted and activated.
    """

    connection = MagicMock()

    existing_result = _make_scalar_result(
        None
    )

    insert_result = MagicMock()
    insert_result.lastrowid = 42

    activate_result = MagicMock()

    connection.execute.side_effect = [
        existing_result,
        insert_result,
        activate_result
    ]

    snapshot_id = (
        _register_and_activate_snapshot(
            connection,
            snapshot_code=" 2026-v1 ",
            tax_year=2026,
            source_filename=(
                " 2026 Roll - Parcels Export.xlsx "
            ),
            loaded_by=" Matthew Phinney ",
            notes=" First 2026 load "
        )
    )

    assert snapshot_id == 42

    assert connection.execute.call_count == 3

    insert_parameters = (
        connection.execute
        .call_args_list[1]
        .args[1]
    )

    assert insert_parameters == {
        "snapshot_code": "2026-v1",
        "tax_year": 2026,
        "source_filename":
            "2026 Roll - Parcels Export.xlsx",
        "loaded_by": "Matthew Phinney",
        "notes": "First 2026 load"
    }

    activation_parameters = (
        connection.execute
        .call_args_list[2]
        .args[1]
    )

    assert activation_parameters == {
        "snapshot_id": 42
    }


def test_duplicate_snapshot_code_is_rejected():
    """
    An existing snapshot code must not be reused.
    """

    connection = MagicMock()

    connection.execute.return_value = (
        _make_scalar_result(1)
    )

    with pytest.raises(
        ValueError,
        match="Snapshot code already exists: 2025"
    ):
        _register_and_activate_snapshot(
            connection,
            snapshot_code="2025",
            tax_year=2025,
            source_filename="2025.xlsx"
        )

    assert connection.execute.call_count == 1


def test_blank_snapshot_code_is_rejected():
    """
    A blank snapshot code should fail before any SQL
    is executed.
    """

    connection = MagicMock()

    with pytest.raises(
        ValueError,
        match="snapshot_code cannot be blank"
    ):
        _register_and_activate_snapshot(
            connection,
            snapshot_code="   ",
            tax_year=2026,
            source_filename="2026.xlsx"
        )

    connection.execute.assert_not_called()


def test_blank_source_filename_is_rejected():
    """
    A blank source filename should fail before any SQL
    is executed.
    """

    connection = MagicMock()

    with pytest.raises(
        ValueError,
        match="source_filename cannot be blank"
    ):
        _register_and_activate_snapshot(
            connection,
            snapshot_code="2026-v1",
            tax_year=2026,
            source_filename="   "
        )

    connection.execute.assert_not_called()


def test_non_integer_tax_year_is_rejected():
    """
    tax_year must be supplied as an integer.
    """

    connection = MagicMock()

    with pytest.raises(
        ValueError,
        match="tax_year must be an integer"
    ):
        _register_and_activate_snapshot(
            connection,
            snapshot_code="2026-v1",
            tax_year="2026",
            source_filename="2026.xlsx"
        )

    connection.execute.assert_not_called()


@pytest.mark.parametrize(
    "tax_year",
    [
        1999,
        2201
    ]
)
def test_out_of_range_tax_year_is_rejected(
        tax_year
):
    """
    Tax years outside the supported range should fail
    before any SQL is executed.
    """

    connection = MagicMock()

    with pytest.raises(
        ValueError,
        match=(
            "tax_year must be between "
            "2000 and 2200"
        )
    ):
        _register_and_activate_snapshot(
            connection,
            snapshot_code="test-v1",
            tax_year=tax_year,
            source_filename="test.xlsx"
        )

    connection.execute.assert_not_called()


def test_missing_snapshot_id_is_rejected():
    """
    Snapshot insertion should fail if MySQL does not
    return an inserted snapshot ID.
    """

    connection = MagicMock()

    existing_result = _make_scalar_result(
        None
    )

    insert_result = MagicMock()
    insert_result.lastrowid = None

    connection.execute.side_effect = [
        existing_result,
        insert_result
    ]

    with pytest.raises(
        RuntimeError,
        match=(
            "Snapshot record was created but no "
            "snapshot_id was returned"
        )
    ):
        _register_and_activate_snapshot(
            connection,
            snapshot_code="2026-v1",
            tax_year=2026,
            source_filename="2026.xlsx"
        )

    assert connection.execute.call_count == 2