# Testing & Validation

[← Back to project README](../README.md)

## Overview

The project uses **pytest** to cover data cleaning, ETL configuration and snapshot handling, read API contracts, administrative suppression/restoration, and regression checks for the validated 2025 dataset.

The completed development environment was documented with **67 passing automated tests** against the validated 2025 snapshot. Results can differ in an unconfigured environment because some tests require MySQL, API environment variables, and the expected active snapshot.

## Test Organization

```text
tests/
├── admin/
│   └── test_admin_associations.py
├── contract/
│   └── test_read_api.py
├── etl/
│   ├── test_data_cleaning.py
│   ├── test_etl_cli.py
│   ├── test_etl_config.py
│   └── test_snapshot_registration.py
├── snapshot_2025/
│   └── test_2025_snapshot.py
└── conftest.py
```

| Group | Coverage | Requires live MySQL? |
|---|---|---|
| `tests/etl` | Cleaning and ETL configuration; validation-only behavior and snapshot registration helpers. | No, for this group's unit tests. |
| `tests/contract` | Read API response structures and endpoint behavior. | Yes. |
| `tests/admin` | API-key-protected suppress/restore/list behavior. | Yes. |
| `tests/snapshot_2025` | Frozen regression expectations for the validated 2025 dataset. | Yes; exact 2025 active snapshot required. |

## Quick Database-Independent Tests

From the repository root in Windows PowerShell:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/etl -v
```

These tests verify the ETL and cleaning behavior without changing a live Treasury database. This is the simplest starting point for a developer who has cloned the repository but has not configured MySQL.

## Full Test Suite

Once the MySQL schema, `.env`, least-privilege accounts, and an active snapshot are configured:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -v
```

The API tests use FastAPI's `TestClient` but still query the configured MySQL database through the application's SQLAlchemy connections.

The administrative tests use real suppression/restoration SQL within **rollback-only test transactions**, so their test changes are not persisted. Do not point integration tests at a production environment without an approved isolation and database-access strategy.

## Run Individual Test Groups

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/contract -v
& ".\.venv\Scripts\python.exe" -m pytest tests/admin -v
& ".\.venv\Scripts\python.exe" -m pytest tests/snapshot_2025 -v
& ".\.venv\Scripts\python.exe" -m pytest tests/etl -v
```

## Validated 2025 Baseline

The regression suite was written against the exact development snapshot with code **`2025`**. If another snapshot code is active, the `tests/snapshot_2025` module is skipped; this is intentional and does not mean that future tax years should reproduce 2025 counts.

| Output | Expected 2025 count |
|---|---:|
| Parcels | 3,874 |
| Resolved entities | 4,954 |
| Parcel/entity roles | 12,050 |
| Entity associations | 299 |
| Association evidence | 477 |
| Entity occurrences | 12,067 |
| Directional association-view rows | 598 |

### Regression Example

The frozen 2025 API regression tests include the following specific results:

- Search `graham` finds `GRAHAM, WILLIAM D`, entity ID `1719`.
- That entity has six distinct associated parcels and six source occurrences.
- Search for `coppercreek` finds `THE COPPER CREEK TRUST`, entity ID `4342`.
- The trust has seven distinct associated parcels, with multiple roles per parcel.
- William Graham's association with that trust has association ID `173`, `High` evidence strength, 20 evidence events, and five distinct evidence rules.

These identifiers are **specific to the frozen 2025 snapshot** and should not be hard-coded into general API clients or assumed stable after a refresh. The `High` label is not a probability or a legal finding.

## Transaction and Refresh Validation

In addition to automated tests, transactional rollback was manually verified in the development project. The loader validates the pipeline output, database schema, loaded row counts, and snapshot registration within its transaction. Failures before commit roll back the generated-data changes.

Duplicate snapshot codes are checked during preflight before generated tables are cleared. Successful refreshes replace the active generated dataset and register a new snapshot; they do not store complete historical dataset copies.

## Reproducibility Notes

- Use a compatible Python environment (development verified on Python 3.12).
- Install requirements into a clean virtual environment; the repository also includes a dependency lock file from development.
- Copy `.env.example` to an untracked `.env` and configure distinct database accounts.
- Use the appropriate SQL scripts to initialize a fresh MySQL schema.
- Use the source worksheet `Only Delinquent Parcels` for the validated 2025 pipeline.
- Run database-independent tests first, followed by database-dependent suites only when their prerequisites are available.
- Preserve the validated 2025 snapshot code `2025` if you intend to run the frozen 2025 regression checks as written.

For setup instructions, see [Installation & Setup](setup.md). For safe loading and rollback semantics, see [Annual Data Refresh](annual-refresh.md).
