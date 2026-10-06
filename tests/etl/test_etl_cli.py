import sys
from unittest.mock import MagicMock

import pandas as pd

import etl_pipeline


def _mock_pipeline_stages(
        monkeypatch
):
    """
    Replace the expensive ETL stages with small test
    DataFrames.

    Returns the fake pipeline outputs so tests can verify
    exactly what would be passed to load_database().
    """

    extracted_df = pd.DataFrame(
        {
            "raw": ["test"]
        }
    )

    clean_df = pd.DataFrame(
        {
            "parcel_number": ["TEST-001"]
        }
    )

    entity_occurrences = pd.DataFrame(
        {
            "occurrence_id": [1],
            "entity_id": [1]
        }
    )

    entities = pd.DataFrame(
        {
            "entity_id": [1]
        }
    )

    parcel_entity_roles = pd.DataFrame(
        {
            "parcel_number": ["TEST-001"],
            "entity_id": [1],
            "role": ["owner"]
        }
    )

    association_evidence = pd.DataFrame()

    entity_associations = pd.DataFrame()

    extract_mock = MagicMock(
        return_value=extracted_df
    )

    monkeypatch.setattr(
        etl_pipeline,
        "extract_data",
        extract_mock
    )

    cleaner = MagicMock()

    cleaner.clean_data.return_value = (
        clean_df
    )

    cleaner_class_mock = MagicMock(
        return_value=cleaner
    )

    monkeypatch.setattr(
        etl_pipeline,
        "DataCleaner",
        cleaner_class_mock
    )

    resolver = MagicMock()

    resolver.build.return_value = (
        entity_occurrences,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations
    )

    resolver_class_mock = MagicMock(
        return_value=resolver
    )

    monkeypatch.setattr(
        etl_pipeline,
        "EntityResolver",
        resolver_class_mock
    )

    return {
        "extracted_df": extracted_df,
        "clean_df": clean_df,
        "entity_occurrences":
            entity_occurrences,
        "entities": entities,
        "parcel_entity_roles":
            parcel_entity_roles,
        "association_evidence":
            association_evidence,
        "entity_associations":
            entity_associations,
        "extract_mock": extract_mock,
        "cleaner": cleaner,
        "resolver": resolver
    }


def test_validate_only_does_not_load_database(
        monkeypatch,
        tmp_path
):
    """
    --validate-only should run extraction, cleaning, and
    entity resolution without calling load_database().
    """

    input_file = (
        tmp_path
        / "2025 Roll - Parcels Export.xlsx"
    )

    input_file.touch()

    pipeline = _mock_pipeline_stages(
        monkeypatch
    )

    load_database_mock = MagicMock()

    monkeypatch.setattr(
        etl_pipeline,
        "load_database",
        load_database_mock
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "etl_pipeline.py",
            "--input",
            str(input_file),
            "--sheet",
            "Only Delinquent Parcels",
            "--year",
            "2025",
            "--validate-only"
        ]
    )

    etl_pipeline.main()

    pipeline[
        "extract_mock"
    ].assert_called_once_with(
        str(input_file),
        "Only Delinquent Parcels"
    )

    pipeline[
        "cleaner"
    ].clean_data.assert_called_once_with(
        pipeline["extracted_df"]
    )

    pipeline[
        "resolver"
    ].build.assert_called_once_with(
        pipeline["clean_df"]
    )

    load_database_mock.assert_not_called()


def test_normal_run_calls_load_database(
        monkeypatch,
        tmp_path
):
    """
    A normal CLI run should pass the completed pipeline
    outputs and snapshot metadata to load_database().
    """

    input_file = (
        tmp_path
        / "2026 Roll - Parcels Export.xlsx"
    )

    input_file.touch()

    pipeline = _mock_pipeline_stages(
        monkeypatch
    )

    load_database_mock = MagicMock()

    monkeypatch.setattr(
        etl_pipeline,
        "load_database",
        load_database_mock
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "etl_pipeline.py",
            "--input",
            str(input_file),
            "--sheet",
            "Only Delinquent Parcels",
            "--year",
            "2026",
            "--snapshot-code",
            "2026-v1",
            "--loaded-by",
            "Matthew Phinney",
            "--notes",
            "Test 2026 snapshot"
        ]
    )

    etl_pipeline.main()

    load_database_mock.assert_called_once_with(
        pipeline["clean_df"],
        pipeline["entities"],
        pipeline["parcel_entity_roles"],
        pipeline["association_evidence"],
        pipeline["entity_associations"],
        pipeline["entity_occurrences"],
        snapshot_code="2026-v1",
        tax_year=2026,
        source_filename=(
            "2026 Roll - Parcels Export.xlsx"
        ),
        loaded_by="Matthew Phinney",
        snapshot_notes="Test 2026 snapshot"
    )