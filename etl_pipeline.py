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

if __name__ == "__main__":
    main()