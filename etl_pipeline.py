import time
import argparse

from data_cleaning import DataCleaner
from extraction import extract_data
from entity_resolution import EntityResolver
from pathlib import Path
from database.load_database import (
    load_database,
    validate_pipeline_for_load
)
from dotenv import load_dotenv

load_dotenv()


def parse_arguments():
    """
    Parse command-line arguments for an annual Treasury
    dataset refresh.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Run the Kalamazoo County Treasury "
            "entity-resolution ETL pipeline."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Path to the source Excel workbook."
        )
    )

    parser.add_argument(
        "--sheet",
        default="Only Delinquent Parcels",
        help=(
            "Excel worksheet to process. "
            "Defaults to 'Only Delinquent Parcels'."
        )
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Tax year represented by the dataset."
    )

    parser.add_argument(
        "--snapshot-code",
        help=(
            "Unique code for this particular "
            "successful load, such as 2026-v1."
        )
    )

    parser.add_argument(
        "--loaded-by",
        default="Treasury ETL",
        help=(
            "Name recorded as the person or process "
            "performing the refresh."
        )
    )

    parser.add_argument(
        "--notes",
        default=None,
        help="Optional snapshot notes."
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Run extraction, cleaning, entity resolution, "
            "and validation without modifying MySQL."
        )
    )

    args = parser.parse_args()

    if args.snapshot_code is not None:
        args.snapshot_code = (
            args.snapshot_code.strip()
        )

    if not 2000 <= args.year <= 2200:
        parser.error(
            "--year must be between 2000 and 2200."
        )

    if (
        not args.validate_only
        and not args.snapshot_code
    ):
        parser.error(
            "--snapshot-code is required unless "
            "--validate-only is used."
        )

    return args


def main():

    total_start = time.perf_counter()

    args = parse_arguments()

    input_path = Path(
        args.input
    )

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Input file does not exist: "
            f"{input_path}"
        )

    print(
        "\n"
        "==========================================\n"
        "KALAMAZOO COUNTY TREASURY ETL\n"
        "=========================================="
    )

    print(
        f"Input file:    {input_path}"
    )

    print(
        f"Worksheet:     {args.sheet}"
    )

    print(
        f"Tax year:      {args.year}"
    )

    print(
        f"Snapshot code: "
        f"{args.snapshot_code or 'N/A - validation only'}"
    )

    # ----------------------------------------------------------
    # Extract
    # ----------------------------------------------------------

    print("\n[1/4] Starting extraction...")
    start = time.perf_counter()

    extracted_df = extract_data(
        str(input_path),
        args.sheet
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

    if args.validate_only:
        validate_pipeline_for_load(
            clean_df,
            entities,
            parcel_entity_roles,
            association_evidence,
            entity_associations,
            entity_occurrences
        )

        print(
            "\n"
            "==========================================\n"
            "VALIDATION-ONLY RUN COMPLETED\n"
            "NO DATABASE CHANGES WERE MADE\n"
            "=========================================="
        )

        print(
            "\nValidation pipeline completed in "
            f"{time.perf_counter() - total_start:.2f} seconds."
        )

        return

    print("\n[4/4] Starting database load...")
    start = time.perf_counter()

    load_database(
        clean_df,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations,
        entity_occurrences,

        snapshot_code=args.snapshot_code,
        tax_year=args.year,
        source_filename=input_path.name,
        loaded_by=args.loaded_by,
        snapshot_notes=args.notes
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