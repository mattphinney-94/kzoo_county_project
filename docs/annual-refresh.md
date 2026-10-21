# Annual Data Refresh

[← Back to project README](../README.md)

## Purpose

The annual ETL pipeline processes a Treasury Excel workbook without requiring Python source-code changes each tax year, provided the new export retains the expected structure. A refresh is **manually initiated**; the repository does not schedule annual loads automatically.

The entry point is [`etl_pipeline.py`](../etl_pipeline.py). Run all commands from the repository root with the configured Python environment.

**Important:** A successful real load **replaces the six generated MySQL tables** with the processed input dataset. Always validate first, confirm the intended input and environment, and maintain appropriate backups. Do not perform a real refresh simply to demonstrate the CLI.

## CLI Arguments

| Argument | Meaning |
|---|---|
| `--input` | Required path to the Excel workbook; may be relative or absolute. |
| `--sheet` | Worksheet name; defaults to `Only Delinquent Parcels`. |
| `--year` | Required tax year, validated to be between 2000 and 2200. |
| `--snapshot-code` | Unique identifier for a successful load; required unless `--validate-only` is set. |
| `--loaded-by` | Name/process recorded in snapshot metadata; defaults to `Treasury ETL`. |
| `--notes` | Optional notes attached to the snapshot record. |
| `--validate-only` | Run the ETL and validate its results **without modifying MySQL**. |

To see command-line help:

```powershell
& ".\.venv\Scripts\python.exe" etl_pipeline.py --help
```

## Step 1 — Validate Without Modifying MySQL

The following Windows PowerShell example uses an illustrative 2026 file path:

```powershell
& ".\.venv\Scripts\python.exe" etl_pipeline.py `
  --input "C:\TreasuryData\2026 Roll - Parcels Export.xlsx" `
  --sheet "Only Delinquent Parcels" `
  --year 2026 `
  --validate-only
```

The pipeline performs extraction, cleaning, entity resolution, association generation, and output validation, but does **not** call the MySQL loader.

A successful validation-only run ends with:

```text
VALIDATION-ONLY RUN COMPLETED
NO DATABASE CHANGES WERE MADE
```

Review the logs and validation results. Stop and investigate errors or unexpectedly changed counts before proceeding.

## Step 2 — Load a New Snapshot

After validation succeeds, use a new snapshot code and the ETL database account configured in `.env`:

```powershell
& ".\.venv\Scripts\python.exe" etl_pipeline.py `
  --input "C:\TreasuryData\2026 Roll - Parcels Export.xlsx" `
  --sheet "Only Delinquent Parcels" `
  --year 2026 `
  --snapshot-code "2026-v1" `
  --loaded-by "Treasury Staff" `
  --notes "Initial validated 2026 delinquent parcel snapshot."
```

In PowerShell, the backtick (`) is a line-continuation character: do not place spaces after it. An equivalent command can be written on one line.

For bash-compatible shells, use a trailing backslash (`\`) rather than a PowerShell backtick.

The ETL records the source filename from `--input` automatically. It does not require the workbook to reside in the project directory.

## Snapshot Codes

A snapshot code identifies one specific processed version of a dataset. Recommended examples:

```text
2026-v1
2026-v2
2027-v1
```

If staff receive a corrected workbook for the same tax year, use a **new** code such as `2026-v2`. Previously used snapshot codes cannot be reused. The pipeline checks for a duplicate code before it clears generated-table rows.

## Transactional Refresh and Rollback

The loader uses a single SQLAlchemy/MySQL transaction for the generated data replacement, database validation, snapshot registration, and snapshot activation:

```text
Validate pipeline outputs
         |
         v
Open database transaction
         |
         v
Validate schema and check snapshot code
         |
         v
Clear generated-table rows
         |
         v
Load and validate new generated rows
         |
         v
Register snapshot and activate it
         |
         v
Commit transaction
```

The six generated tables use MySQL's transactional InnoDB storage engine. If an operation fails **before commit**, the transaction is rolled back rather than leaving a partially refreshed active dataset. Duplicate snapshot codes are rejected during preflight, before generated tables are cleared.

A successful refresh replaces rows in:

- `parcels`
- `entities`
- `parcel_entity_roles`
- `entity_associations`
- `association_evidence`
- `entity_occurrences`

The following administrative tables are preserved across ordinary refreshes:

- `data_snapshots`
- `active_data_snapshot`
- `association_suppressions`

Suppressions are snapshot-specific. Existing suppression history is retained, but does not automatically apply to unrelated associations in a new active snapshot.

## History, Backups, and Recovery

The snapshot system stores **load metadata and a pointer to the active dataset**, not independent historical copies of all generated tables. Transactional rollback protects against incomplete loads; it is **not** a substitute for backups after a successful commit.

Retain approved source workbooks and database backups according to County policies. A prior dataset may be reconstructed by reprocessing its original workbook, but this is a **new real load**, requires a new unused snapshot code, and changes the active generated tables.

## Operational Checklist

1. Confirm the intended workbook, worksheet, tax year, and database environment.
2. Back up the database and retain the source workbook under approved storage controls.
3. Run `--validate-only` and investigate all errors.
4. Choose an unused snapshot code and review any expected changes in record counts.
5. Execute the real refresh only when approved.
6. Confirm `GET /api/health` and representative searches against the new dataset.
7. Record the snapshot code, source version, and load outcome for future reference.

See [Installation & Setup](setup.md), [Database Documentation](database.md), and [Testing & Validation](testing.md).
