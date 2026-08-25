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

    """
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

    #########################################################
    # Three-way entity classification checks
    #########################################################
    entity_occurrences[
        "entity_type"
    ].value_counts(
        dropna=False
    )

    unknown_names = (
        entity_occurrences.loc[
            entity_occurrences["entity_type"] == "Unknown",
            "entity_name"
        ]
        .value_counts()
        .rename_axis("entity_name")
        .reset_index(name="occurrence_count")
    )

    print(
        f"Unique Unknown names: "
        f"{len(unknown_names):,}"
    )

    unknown_names.head(100)

    unknown_joint_names = (
        entity_occurrences[
            (entity_occurrences["entity_type"] == "Unknown")
            &
            (
                entity_occurrences["entity_name"]
                .str.contains(
                    r"&|\bAND\b|/",
                    regex=True,
                    na=False
                )
            )
            ]
    )

    print(
        f"Unknown occurrences containing joint-name markers: "
        f"{len(unknown_joint_names):,}"
    )

    print(unknown_joint_names[
        "entity_name"
    ].value_counts())

    unknown_entity_columns = entities.loc[
        entities["entity_type"] == "Unknown"
    ]

    print(unknown_entity_columns.head(500))
    """

    source_occurrence_count = (
        entity_occurrences[
            "source_occurrence_id"
        ]
        .nunique()
    )

    expanded_occurrence_count = len(
        entity_occurrences
    )

    derived_occurrence_increase = (
        expanded_occurrence_count
        - source_occurrence_count
    )

    print(
        "Unique source occurrences:",
        f"{source_occurrence_count:,}"
    )

    print(
        "Entity occurrences after Joint expansion:",
        f"{expanded_occurrence_count:,}"
    )

    print(
        "Additional occurrences created by decomposition:",
        f"{derived_occurrence_increase:,}"
    )

    print(
        "Expanded Joint-derived occurrences:",
        entity_occurrences[
            "joint_expanded"
        ].sum()
    )

    medium_joint_candidates = (
        entity_occurrences[
            (entity_occurrences["entity_type"] == "Joint")
            &
            (
                    entity_occurrences[
                        "joint_parse_confidence"
                    ] == "Medium"
            )
            ]
    )

    print(
        "Medium-confidence Joint candidates "
        "not yet expanded:",
        len(medium_joint_candidates)
    )

    medium_joint_candidates[
        [
            "entity_name",
            "joint_parse_rule",
            "joint_parse_confidence"
        ]
    ].drop_duplicates().head(100)

if __name__ == "__main__":
    main()