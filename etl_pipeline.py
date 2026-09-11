import time
import pandas as pd

from data_cleaning import DataCleaner
from extraction import extract_data
from entity_resolution import EntityResolver
from database.load_database import load_database


pd.set_option("display.width", 1000)
pd.set_option("display.max_columns", None)


def main():

    total_start = time.perf_counter()

    # ----------------------------------------------------------
    # Extract
    # ----------------------------------------------------------

    print("\n[1/4] Starting extraction...")
    start = time.perf_counter()

    extracted_df = extract_data(
        "2025 Roll - Parcels Export.xlsx",
        "Only Delinquent Parcels"
    )

    print(
        f"[1/4] Extraction complete "
        f"({time.perf_counter() - start:.2f} seconds)"
    )


    # ----------------------------------------------------------
    # Clean
    # ----------------------------------------------------------

    print("\n[2/4] Starting cleaning...")
    start = time.perf_counter()

    cleaner = DataCleaner()

    clean_df = cleaner.clean_data(
        extracted_df
    )

    print(
        f"[2/4] Cleaning complete "
        f"({time.perf_counter() - start:.2f} seconds)"
    )


    # ----------------------------------------------------------
    # Entity Resolution
    # ----------------------------------------------------------

    print("\n[3/4] Starting entity resolution...")
    start = time.perf_counter()

    (
        entity_occurrences,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations
    ) = EntityResolver().build(
        clean_df
    )

    print(
        f"[3/4] Entity resolution complete "
        f"({time.perf_counter() - start:.2f} seconds)"
    )


    # ----------------------------------------------------------
    # Load Database
    # ----------------------------------------------------------

    print("\n[4/4] Starting database load...")
    start = time.perf_counter()

    load_database(
        clean_df=clean_df,
        entities=entities,
        parcel_entity_roles=parcel_entity_roles,
        association_evidence=association_evidence,
        entity_associations=entity_associations,
        entity_occurrences=entity_occurrences
    )

    print(
        f"[4/4] Database load complete "
        f"({time.perf_counter() - start:.2f} seconds)"
    )


    print(
        "\nEntire ETL pipeline completed in "
        f"{time.perf_counter() - total_start:.2f} seconds."
    )


if __name__ == "__main__":
    main()