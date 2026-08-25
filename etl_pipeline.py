# Import Packages
import pandas as pd

# Import from local files
from data_cleaning import DataCleaner
from extraction import extract_data
from entity_resolution import EntityResolver

# Set pandas display options
pd.set_option("display.width", 1000)
pd.set_option("display.max_columns", None)


def main():

    # ----------------------------------------------------------
    # Extract
    # ----------------------------------------------------------

    extracted_df = extract_data(
        "2025 Roll - Parcels Export.xlsx",
        "Only Delinquent Parcels"
    )


    # ----------------------------------------------------------
    # Clean
    # ----------------------------------------------------------

    cleaner = DataCleaner()

    clean_df = cleaner.clean_data(
        extracted_df
    )


    # ----------------------------------------------------------
    # Entity Resolution
    # ----------------------------------------------------------

    (
        entity_occurrences,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations
    ) = EntityResolver().build(
        clean_df
    )


    # ----------------------------------------------------------
    # Entity Occurrences Checks
    # ----------------------------------------------------------

    print("\nENTITY OCCURRENCES")
    print("-" * 80)

    print(entity_occurrences.head(20))

    print(
        f"\nTotal entity occurrences: "
        f"{len(entity_occurrences):,}"
    )

    print("\nEntity types:")
    print(
        entity_occurrences[
            "entity_type"
        ].value_counts(
            dropna=False
        )
    )

    print("\nOrganization types:")
    print(
        entity_occurrences[
            "organization_type"
        ].value_counts(
            dropna=False
        )
    )


    # ----------------------------------------------------------
    # Entities Checks
    # ----------------------------------------------------------

    print("\n\nENTITIES")
    print("-" * 80)

    print(entities.head(20))

    print(
        f"\nTotal entities: "
        f"{len(entities):,}"
    )

    print(
        f"Unique entity names: "
        f"{entities['canonical_name'].nunique():,}"
    )


    # ----------------------------------------------------------
    # Resolution Validation
    # ----------------------------------------------------------

    print("\n\nRESOLUTION VALIDATION")
    print("-" * 80)

    # Every occurrence should have an entity_id
    missing_entity_ids = (
        entity_occurrences[
            "entity_id"
        ]
        .isna()
        .sum()
    )

    print(
        f"Occurrences missing entity_id: "
        f"{missing_entity_ids:,}"
    )

    # Every entity_id referenced by an occurrence should
    # exist in the entities table.
    invalid_entity_ids = (
        set(entity_occurrences["entity_id"])
        - set(entities["entity_id"])
    )

    print(
        f"Invalid entity_id references: "
        f"{len(invalid_entity_ids):,}"
    )

    # occurrence_count should account for every occurrence.
    total_occurrence_count = (
        entities[
            "occurrence_count"
        ]
        .sum()
    )

    print(
        f"Sum of entity occurrence counts: "
        f"{total_occurrence_count:,}"
    )

    print(
        f"Actual entity occurrences: "
        f"{len(entity_occurrences):,}"
    )

    # entity_id should be unique.
    duplicate_entity_ids = (
        entities[
            "entity_id"
        ]
        .duplicated()
        .sum()
    )

    print(
        f"Duplicate entity IDs: "
        f"{duplicate_entity_ids:,}"
    )

    # There should no longer be exact duplicate resolved entities.
    duplicate_entities = (
        entities
        .duplicated(
            subset=[
                "entity_type",
                "canonical_name",
                "canonical_address"
            ]
        )
        .sum()
    )

    print(
        f"Exact duplicate resolved entities: "
        f"{duplicate_entities:,}"
    )


if __name__ == "__main__":
    main()