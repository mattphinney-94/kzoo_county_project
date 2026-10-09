"""
Load the completed Kalamazoo County Treasury entity-resolution
pipeline outputs into the MySQL production schema.

This module assumes that the database schema has already been
created and that the following MySQL objects exist:

    parcels
    entities
    parcel_entity_roles
    entity_associations
    association_evidence
    entity_occurrences

    data_snapshots
    active_data_snapshot
    association_suppressions

    entity_association_neighbors   (view)
"""

import os

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ==========================================================
# DATABASE CONFIGURATION
# ==========================================================

def _get_database_config(
        db_user=None,
        db_password=None
):
    """
    Read ETL database configuration from environment variables.

    Explicit db_user/db_password values may be supplied for
    testing or other controlled use.
    """

    db_host = os.getenv(
        "TREASURY_DB_HOST",
        "localhost"
    )

    db_port = int(
        os.getenv(
            "TREASURY_DB_PORT",
            "3306"
        )
    )

    db_name = os.getenv(
        "TREASURY_DB_NAME",
        "kalamazoo_county_treasury"
    )

    db_user = (
        db_user
        or os.getenv(
            "TREASURY_ETL_DB_USER"
        )
    )

    db_password = (
        db_password
        or os.getenv(
            "TREASURY_ETL_DB_PASSWORD"
        )
    )

    missing_settings = []

    if not db_user:
        missing_settings.append(
            "TREASURY_ETL_DB_USER"
        )

    if not db_password:
        missing_settings.append(
            "TREASURY_ETL_DB_PASSWORD"
        )

    if missing_settings:
        raise RuntimeError(
            "Missing required ETL database "
            "environment variables: "
            f"{', '.join(missing_settings)}"
        )

    return {
        "host": db_host,
        "port": db_port,
        "name": db_name,
        "user": db_user,
        "password": db_password
    }

# ==========================================================
# PARCEL TABLE CREATION
# ==========================================================

def _create_parcels_dataframe(clean_df):
    """
    Create the normalized parcels table from clean_df.

    Owner/taxpayer fields are intentionally excluded because
    those relationships are represented by entities and
    parcel_entity_roles.
    """

    parcel_columns = [
        "parcel_number",
        "property_address",
        "principal_residence_exemption_percentage",
        "property_class",
        "tax_value",
        "assessed_value",
        "state_equalized_value"
    ]

    missing_columns = (
        set(parcel_columns)
        -
        set(clean_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "clean_df is missing parcel columns: "
            f"{sorted(missing_columns)}"
        )

    parcels = (
        clean_df[
            parcel_columns
        ]
        .copy()
    )

    if parcels[
        "parcel_number"
    ].isna().any():
        raise ValueError(
            "parcels contains missing parcel numbers."
        )

    if parcels[
        "parcel_number"
    ].duplicated().any():
        duplicates = (
            parcels.loc[
                parcels[
                    "parcel_number"
                ].duplicated(
                    keep=False
                ),
                "parcel_number"
            ]
            .unique()
        )

        raise ValueError(
            "Duplicate parcel numbers found while "
            "creating parcels table: "
            f"{duplicates[:10].tolist()}"
        )

    return parcels


# ==========================================================
# SQL NULL PREPARATION
# ==========================================================

def _prepare_for_sql(
        df,
        nullable_string_columns=None
):
    """
    Prepare a DataFrame for insertion into MySQL.

    Missing pandas values become Python None.

    Empty strings are converted to None only for columns
    where blank means 'no value'. The original DataFrames
    are not modified.
    """

    result = df.copy()

    nullable_string_columns = (
        nullable_string_columns
        or []
    )

    for column in nullable_string_columns:

        if column not in result.columns:
            continue

        result[column] = (
            result[column]
            .replace(
                "",
                None
            )
        )

    # Convert pandas NA / NaN / NaT to Python None.
    #
    # Casting to object first prevents numeric columns from
    # immediately converting None back into NaN.
    result = result.astype(object)

    result = result.where(
        pd.notna(result),
        None
    )

    return result


# ==========================================================
# DATAFRAME VALIDATION
# ==========================================================

def _validate_pipeline_outputs(
        parcels,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations,
        entity_occurrences
):
    """
    Validate important pipeline invariants before touching
    the database.
    """

    print(
        "Validating pipeline outputs..."
    )

    # ------------------------------------------------------
    # Primary-key uniqueness
    # ------------------------------------------------------

    if not parcels[
        "parcel_number"
    ].is_unique:
        raise ValueError(
            "parcels.parcel_number is not unique."
        )

    if not entities[
        "entity_id"
    ].is_unique:
        raise ValueError(
            "entities.entity_id is not unique."
        )

    if not association_evidence[
        "evidence_id"
    ].is_unique:
        raise ValueError(
            "association_evidence.evidence_id "
            "is not unique."
        )

    if not entity_associations[
        "association_id"
    ].is_unique:
        raise ValueError(
            "entity_associations.association_id "
            "is not unique."
        )

    if not entity_occurrences[
        "occurrence_id"
    ].is_unique:
        raise ValueError(
            "entity_occurrences.occurrence_id "
            "is not unique."
        )

    # ------------------------------------------------------
    # Composite-grain uniqueness
    # ------------------------------------------------------

    if parcel_entity_roles.duplicated(
        subset=[
            "parcel_number",
            "entity_id",
            "role"
        ]
    ).any():
        raise ValueError(
            "parcel_entity_roles contains duplicate "
            "(parcel_number, entity_id, role) rows."
        )

    if entity_associations.duplicated(
        subset=[
            "entity_id_a",
            "entity_id_b"
        ]
    ).any():
        raise ValueError(
            "entity_associations contains duplicate "
            "entity pairs."
        )

    # ------------------------------------------------------
    # Normalized association pairs
    # ------------------------------------------------------

    if not (
        entity_associations[
            "entity_id_a"
        ]
        <
        entity_associations[
            "entity_id_b"
        ]
    ).all():
        raise ValueError(
            "entity_associations contains an "
            "unnormalized or self-referencing pair."
        )

    if not (
        association_evidence[
            "entity_id_a"
        ]
        <
        association_evidence[
            "entity_id_b"
        ]
    ).all():
        raise ValueError(
            "association_evidence contains an "
            "unnormalized or self-referencing pair."
        )

    # ------------------------------------------------------
    # Foreign-key-domain validation
    # ------------------------------------------------------

    valid_entity_ids = set(
        entities[
            "entity_id"
        ]
    )

    valid_parcels = set(
        parcels[
            "parcel_number"
        ]
    )

    for column in [
        parcel_entity_roles[
            "entity_id"
        ],
        entity_associations[
            "entity_id_a"
        ],
        entity_associations[
            "entity_id_b"
        ],
        association_evidence[
            "entity_id_a"
        ],
        association_evidence[
            "entity_id_b"
        ],
        entity_occurrences[
            "entity_id"
        ]
    ]:
        if not set(
            column.dropna()
        ).issubset(
            valid_entity_ids
        ):
            raise ValueError(
                "A table references an entity_id "
                "that does not exist in entities."
            )

    for column in [
        parcel_entity_roles[
            "parcel_number"
        ],
        association_evidence[
            "parcel_number_a"
        ],
        association_evidence[
            "parcel_number_b"
        ],
        entity_occurrences[
            "parcel_number"
        ]
    ]:
        values = set(
            column.dropna()
        )

        if not values.issubset(
            valid_parcels
        ):
            raise ValueError(
                "A table references a parcel_number "
                "that does not exist in parcels."
            )

    # ------------------------------------------------------
    # Every evidence pair must exist in Stage 6
    # ------------------------------------------------------

    association_pairs = set(
        zip(
            entity_associations[
                "entity_id_a"
            ],
            entity_associations[
                "entity_id_b"
            ]
        )
    )

    evidence_pairs = set(
        zip(
            association_evidence[
                "entity_id_a"
            ],
            association_evidence[
                "entity_id_b"
            ]
        )
    )

    if not evidence_pairs.issubset(
        association_pairs
    ):
        raise ValueError(
            "association_evidence contains a pair "
            "that is missing from entity_associations."
        )

    # ------------------------------------------------------
    # Stage 6 reconciliation
    # ------------------------------------------------------

    if (
        entity_associations[
            "evidence_count"
        ].sum()
        !=
        len(
            association_evidence
        )
    ):
        raise ValueError(
            "Stage 6 evidence counts do not reconcile "
            "to association_evidence."
        )

    # ------------------------------------------------------
    # Entity occurrence reconciliation
    # ------------------------------------------------------

    if (
        entities[
            "occurrence_count"
        ].sum()
        !=
        len(
            entity_occurrences
        )
    ):
        raise ValueError(
            "entities.occurrence_count does not "
            "reconcile to entity_occurrences."
        )

    print(
        "Pipeline validation passed."
    )

def validate_pipeline_for_load(
        clean_df,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations,
        entity_occurrences
):
    """
    Build the parcels output and validate the completed
    pipeline without connecting to or modifying MySQL.

    Returns the validated parcels DataFrame.
    """

    print("Creating parcels DataFrame...")

    parcels = _create_parcels_dataframe(
        clean_df
    )

    print("Parcels DataFrame created.")

    _validate_pipeline_outputs(
        parcels,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations,
        entity_occurrences
    )

    return parcels

# ==========================================================
# DATABASE SCHEMA VALIDATION
# ==========================================================

def _validate_database_schema(
        connection,
        database_name
):
    """
    Confirm that create_schema.sql has already created all
    required tables and the association-neighbor view.
    """

    required_tables = {
        "parcels",
        "entities",
        "parcel_entity_roles",
        "entity_associations",
        "association_evidence",
        "entity_occurrences",

        "data_snapshots",
        "active_data_snapshot",
        "association_suppressions"
    }

    table_query = text(
        """
        SELECT
            table_name,
            engine
        FROM information_schema.tables
        WHERE table_schema = :database_name
          AND table_type = 'BASE TABLE'
        """
    )

    result = connection.execute(
        table_query,
        {
            "database_name": database_name
        }
    )

    table_engines = {
        row[0]: row[1]
        for row in result
    }

    existing_tables = set(
        table_engines
    )

    missing_tables = (
        required_tables
        -
        existing_tables
    )

    if missing_tables:
        raise RuntimeError(
            "Database schema is missing tables: "
            f"{sorted(missing_tables)}"
        )

    non_innodb_tables = sorted(
        table_name
        for table_name in required_tables
        if table_engines[
            table_name
        ].upper() != "INNODB"
    )

    if non_innodb_tables:
        raise RuntimeError(
            "The following required tables are not "
            "using InnoDB: "
            f"{non_innodb_tables}. "
            "Transactional ETL rollback requires InnoDB."
        )

    view_query = text(
        """
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = :database_name
          AND table_name =
              'entity_association_neighbors'
        """
    )

    view_exists = (
        connection.execute(
            view_query,
            {
                "database_name": database_name
            }
        )
        .first()
        is not None
    )

    if not view_exists:
        raise RuntimeError(
            "entity_association_neighbors view "
            "does not exist."
        )


# ==========================================================
# CLEAR EXISTING DATA
# ==========================================================

def _clear_database(
        connection
):
    """
    Remove existing data in reverse foreign-key dependency
    order.

    DELETE is used rather than DROP/TRUNCATE so the schema
    remains intact and normal foreign-key enforcement stays
    enabled.
    """

    print(
        "Clearing existing database rows..."
    )

    delete_order = [
        "association_evidence",
        "entity_occurrences",
        "parcel_entity_roles",
        "entity_associations",
        "entities",
        "parcels"
    ]

    for table_name in delete_order:
        connection.execute(
            text(
                f"DELETE FROM `{table_name}`"
            )
        )


# ==========================================================
# TABLE INSERTION
# ==========================================================

def _insert_dataframe(
        connection,
        table_name,
        df
):
    """
    Append one DataFrame to an existing MySQL table.

    The database schema must already exist. pandas is never
    allowed to replace or create the tables.
    """

    print(
        f"Loading {table_name}: "
        f"{len(df):,} rows..."
    )

    df.to_sql(
        name=table_name,
        con=connection,
        if_exists="append",
        index=False,
        chunksize=1000,
        method="multi"
    )


# ==========================================================
# POST-LOAD DATABASE VALIDATION
# ==========================================================

def _validate_loaded_database(
        connection,
        expected_counts
):
    """
    Query MySQL directly and compare database row counts
    against the DataFrames that were loaded.
    """

    print(
        "\nValidating database row counts..."
    )

    actual_counts = {}

    for table_name in expected_counts:

        row_count = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM `{table_name}`
                """
            )
        ).scalar_one()

        actual_counts[
            table_name
        ] = row_count

    for table_name, expected in expected_counts.items():

        actual = actual_counts[
            table_name
        ]

        print(
            f"{table_name:<25} "
            f"expected={expected:>7,}   "
            f"actual={actual:>7,}"
        )

        if actual != expected:
            raise RuntimeError(
                f"{table_name} row-count mismatch: "
                f"expected {expected}, "
                f"found {actual}."
            )

    # ------------------------------------------------------
    # Validate directional association view
    # ------------------------------------------------------

    neighbor_count = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM entity_association_neighbors
            """
        )
    ).scalar_one()

    expected_neighbor_count = (
        expected_counts[
            "entity_associations"
        ]
        * 2
    )

    print(
        f"{'entity_association_neighbors':<25} "
        f"expected={expected_neighbor_count:>7,}   "
        f"actual={neighbor_count:>7,}"
    )

    if (
        neighbor_count
        !=
        expected_neighbor_count
    ):
        raise RuntimeError(
            "entity_association_neighbors "
            "row-count mismatch."
        )

    print(
        "\nDatabase validation passed."
    )

# ==========================================================
# SNAPSHOT REGISTRATION
# ==========================================================

def _normalize_snapshot_metadata(
        snapshot_code,
        tax_year,
        source_filename,
        loaded_by=None,
        notes=None
):
    """
    Validate and normalize metadata for a data snapshot.
    """

    if not isinstance(snapshot_code, str):
        raise ValueError(
            "snapshot_code must be a string."
        )

    snapshot_code = snapshot_code.strip()

    if not snapshot_code:
        raise ValueError(
            "snapshot_code cannot be blank."
        )

    if not isinstance(source_filename, str):
        raise ValueError(
            "source_filename must be a string."
        )

    source_filename = source_filename.strip()

    if not source_filename:
        raise ValueError(
            "source_filename cannot be blank."
        )

    if (
        isinstance(tax_year, bool)
        or not isinstance(tax_year, int)
    ):
        raise ValueError(
            "tax_year must be an integer."
        )

    if not 2000 <= tax_year <= 2200:
        raise ValueError(
            "tax_year must be between 2000 and 2200."
        )

    if loaded_by is not None:
        if not isinstance(loaded_by, str):
            raise ValueError(
                "loaded_by must be a string or None."
            )

        loaded_by = (
            loaded_by.strip()
            or None
        )

    if notes is not None:
        if not isinstance(notes, str):
            raise ValueError(
                "notes must be a string or None."
            )

        notes = (
            notes.strip()
            or None
        )

    return (
        snapshot_code,
        tax_year,
        source_filename,
        loaded_by,
        notes
    )

def _ensure_snapshot_code_available(
        connection,
        snapshot_code
):
    """
    Confirm that a snapshot code has not already been used.
    """

    existing_snapshot_query = text(
        """
        SELECT snapshot_id
        FROM data_snapshots
        WHERE snapshot_code = :snapshot_code
        """
    )

    existing_snapshot_id = (
        connection.execute(
            existing_snapshot_query,
            {
                "snapshot_code":
                    snapshot_code
            }
        )
        .scalar_one_or_none()
    )

    if existing_snapshot_id is not None:
        raise ValueError(
            "Snapshot code already exists: "
            f"{snapshot_code}"
        )

def _register_and_activate_snapshot(
        connection,
        *,
        snapshot_code,
        tax_year,
        source_filename,
        loaded_by=None,
        notes=None
):
    """
    Record a successfully loaded data snapshot and mark it as
    the snapshot currently represented by the generated tables.

    This function must be called inside the same transaction as
    the generated-table refresh.
    """

    (
        snapshot_code,
        tax_year,
        source_filename,
        loaded_by,
        notes
    ) = _normalize_snapshot_metadata(
        snapshot_code,
        tax_year,
        source_filename,
        loaded_by,
        notes
    )

    _ensure_snapshot_code_available(
        connection,
        snapshot_code
    )

    insert_snapshot_query = text(
        """
        INSERT INTO data_snapshots (
            snapshot_code,
            tax_year,
            source_filename,
            loaded_by,
            notes
        )
        VALUES (
            :snapshot_code,
            :tax_year,
            :source_filename,
            :loaded_by,
            :notes
        )
        """
    )

    result = connection.execute(
        insert_snapshot_query,
        {
            "snapshot_code":
                snapshot_code,

            "tax_year":
                tax_year,

            "source_filename":
                source_filename,

            "loaded_by":
                loaded_by,

            "notes":
                notes
        }
    )

    snapshot_id = result.lastrowid

    if snapshot_id is None:
        raise RuntimeError(
            "Snapshot record was created but no "
            "snapshot_id was returned."
        )

    activate_snapshot_query = text(
        """
        INSERT INTO active_data_snapshot (
            singleton_id,
            snapshot_id
        )
        VALUES (
            1,
            :snapshot_id
        )

        ON DUPLICATE KEY UPDATE
            snapshot_id = :snapshot_id
        """
    )

    connection.execute(
        activate_snapshot_query,
        {
            "snapshot_id":
                snapshot_id
        }
    )

    return snapshot_id

# ==========================================================
# PUBLIC LOAD FUNCTION
# ==========================================================

def load_database(
        clean_df,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations,
        entity_occurrences,
        *,
        snapshot_code,
        tax_year,
        source_filename,
        loaded_by=None,
        snapshot_notes=None,
        db_user=None,
        db_password=None
):
    """
    Validate and load the completed pipeline into MySQL.

    All deletes and inserts happen inside one transaction.
    If anything fails, the transaction is rolled back.
    """

    (
        snapshot_code,
        tax_year,
        source_filename,
        loaded_by,
        snapshot_notes
    ) = _normalize_snapshot_metadata(
        snapshot_code,
        tax_year,
        source_filename,
        loaded_by,
        snapshot_notes
    )

    parcels = validate_pipeline_for_load(
        clean_df,
        entities,
        parcel_entity_roles,
        association_evidence,
        entity_associations,
        entity_occurrences
    )

    database_config = (
        _get_database_config(
            db_user=db_user,
            db_password=db_password
        )
    )

    print("Preparing DataFrames for SQL...")

    # ------------------------------------------------------
    # Prepare SQL-friendly copies
    # ------------------------------------------------------

    parcels_sql = _prepare_for_sql(
        parcels,
        nullable_string_columns=[
            "property_address",
            "property_class"
        ]
    )

    entities_sql = _prepare_for_sql(
        entities,
        nullable_string_columns=[
            "canonical_address",
            "organization_type",
            "organization_classification_confidence"
        ]
    )

    parcel_entity_roles_sql = (
        _prepare_for_sql(
            parcel_entity_roles
        )
    )

    entity_associations_sql = (
        _prepare_for_sql(
            entity_associations
        )
    )

    association_evidence_sql = (
        _prepare_for_sql(
            association_evidence,
            nullable_string_columns=[
                "parcel_number_a",
                "parcel_number_b",
                "shared_address",
                "address_type"
            ]
        )
    )

    entity_occurrences_sql = (
        _prepare_for_sql(
            entity_occurrences,
            nullable_string_columns=[
                "associated_address",
                "owner_line_continuation_rule",
                "joint_parse_rule",
                "joint_parse_confidence",
                "organization_type",
                "organization_classification_confidence",
                "address_source"
            ]
        )
    )

    print("DataFrames prepared for SQL.")
    print("Ready to connect to MySQL.")

    # ----------------------------------------------------------
    # Expected row counts
    # ----------------------------------------------------------

    expected_counts = {
        "parcels":
            len(
                parcels_sql
            ),

        "entities":
            len(
                entities_sql
            ),

        "parcel_entity_roles":
            len(
                parcel_entity_roles_sql
            ),

        "entity_associations":
            len(
                entity_associations_sql
            ),

        "association_evidence":
            len(
                association_evidence_sql
            ),

        "entity_occurrences":
            len(
                entity_occurrences_sql
            )
    }

    print(
        "\nRows to load:"
    )

    for table_name, count in expected_counts.items():
        print(
            f"  {table_name:<25} "
            f"{count:>7,}"
        )

    database_url = URL.create(
        drivername="mysql+pymysql",
        username=database_config["user"],
        password=database_config["password"],
        host=database_config["host"],
        port=database_config["port"],
        database=database_config["name"]
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 10
        }
    )

    try:

        print(
            "\nOpening MySQL connection..."
        )

        with engine.begin() as connection:

            print(
                "MySQL connection established."
            )

            _validate_database_schema(
                connection,
                database_config["name"]
            )

            _ensure_snapshot_code_available(
                connection,
                snapshot_code
            )

            _clear_database(
                connection
            )

            # ----------------------------------------------
            # Foreign-key-safe loading order
            # ----------------------------------------------

            _insert_dataframe(
                connection,
                "parcels",
                parcels_sql
            )

            _insert_dataframe(
                connection,
                "entities",
                entities_sql
            )

            _insert_dataframe(
                connection,
                "parcel_entity_roles",
                parcel_entity_roles_sql
            )

            # Stage 6 is loaded before Stage 5 because
            # association_evidence has a composite foreign
            # key to entity_associations.

            _insert_dataframe(
                connection,
                "entity_associations",
                entity_associations_sql
            )

            _insert_dataframe(
                connection,
                "association_evidence",
                association_evidence_sql
            )

            _insert_dataframe(
                connection,
                "entity_occurrences",
                entity_occurrences_sql
            )

            _validate_loaded_database(
                connection,
                expected_counts
            )

            snapshot_id = (
                _register_and_activate_snapshot(
                    connection,
                    snapshot_code=snapshot_code,
                    tax_year=tax_year,
                    source_filename=source_filename,
                    loaded_by=loaded_by,
                    notes=snapshot_notes
                )
            )

            print(
                "\nRegistered data snapshot:"
            )

            print(
                f"  snapshot_id:   {snapshot_id}"
            )

            print(
                f"  snapshot_code: {snapshot_code}"
            )

            print(
                f"  tax_year:      {tax_year}"
            )

        print(
            "\n"
            "==========================================\n"
            "DATABASE LOAD COMPLETED SUCCESSFULLY\n"
            "=========================================="
        )

    finally:
        engine.dispose()