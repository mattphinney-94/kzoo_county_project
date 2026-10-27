"""Mocked API endpoint: no MySQL service or personal .env file required."""

import sys
import types
from unittest.mock import MagicMock


def test_fuzzy_api_returns_three_distinct_entities(monkeypatch):
    # Values are placeholders: the test never opens a real DB connection.
    for key, value in (
        ("TREASURY_DB_HOST", "localhost"),
        ("TREASURY_DB_NAME", "test_only"),
        ("TREASURY_DB_USER", "test_only"),
        ("TREASURY_DB_PASSWORD", "placeholder_no_real_connection"),
    ):
        monkeypatch.setenv(key, value)

    stub_db = types.ModuleType("api.database")
    stub_db.engine = MagicMock()
    stub_db.get_active_snapshot_id = lambda connection: 1
    monkeypatch.setitem(sys.modules, "api.database", stub_db)
    from api.routers import entities

    columns = {
        "entity_type": "Person",
        "organization_type": None,
        "organization_classification_confidence": None,
        "occurrence_count": 1,
        "source_entity_name": None,
    }
    fuzzy_rows = [
        {"entity_id": i, "canonical_name": "GRAHAM, WILLIAM D",
         "canonical_address": address, **columns}
        for i, address in (
            (1710, "Portland, OR"),
            (1711, "Galesburg, MI"),
            (1719, "PO BOX 366"),
        )
    ]
    first_result = MagicMock()
    first_result.mappings.return_value.all.return_value = []
    fuzzy_result = MagicMock()
    fuzzy_result.mappings.return_value.all.return_value = fuzzy_rows

    connection = MagicMock()
    connection.execute.side_effect = [first_result, fuzzy_result]
    mocked_engine = MagicMock()
    mocked_engine.connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(entities, "engine", mocked_engine)

    result = entities.search_entities(q="Will Grahm", limit=25)
    assert result["result_count"] == 3
    assert {entry["entity_id"] for entry in result["results"]} == {
        1710, 1711, 1719
    }
    assert connection.execute.call_count == 2
