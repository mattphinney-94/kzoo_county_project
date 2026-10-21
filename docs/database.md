# Database Documentation

[← Back to project README](../README.md)

## Overview

The project stores the processed dataset in **MySQL**. The generated tables contain the **currently active** processed dataset; a successful annual refresh replaces their contents. Separate persistent tables retain snapshot metadata and administrative suppression history.

The SQL definitions are in:

- [`database/create_schema.sql`](../database/create_schema.sql) — generated tables and the association-neighbors view.
- [`database/admin_schema.sql`](../database/admin_schema.sql) — snapshot and suppression-management tables.

Run `create_schema.sql` first, then `admin_schema.sql`, on a **new** database setup. The first script contains ordinary `CREATE TABLE` statements and is not an annual refresh script. Do not re-run schema-creation scripts against an established database without reviewing their effects.

## Generated Tables

The annual ETL refresh replaces rows in the following six tables:

| Table | Description |
|---|---|
| `parcels` | One row per delinquent parcel, including property address and available property/valuation fields. |
| `entities` | Resolved entities with canonical name, type, address, and occurrence count. |
| `parcel_entity_roles` | Unique `(parcel_number, entity_id, role)` records connecting entities to parcels. |
| `entity_associations` | One normalized record per associated entity pair, with confidence and evidence counts. |
| `association_evidence` | Rule-level evidence supporting associated entity pairs, including parcel, role, or address details. |
| `entity_occurrences` | Traceable source-name occurrences retained from the extraction and resolution process. |

### Directional Association View

`entity_association_neighbors` is a MySQL view that exposes both lookup directions for each normalized association. The base `entity_associations` table stores a pair once, with `entity_id_a < entity_id_b`; the view makes it possible to query associations from either entity.

### Load Order

The loader inserts generated data in this order:

1. `parcels`
2. `entities`
3. `parcel_entity_roles`
4. `entity_associations`
5. `association_evidence`
6. `entity_occurrences`

`entity_associations` is loaded before `association_evidence` because evidence rows have a foreign-key relationship to the association pair. The loader also clears existing generated rows in a foreign-key-safe order.

## Persistent Tables

The following tables are **not** cleared by an ordinary annual ETL refresh:

### `data_snapshots`

Records successful loads, including:

- Unique snapshot code (for example, `2026-v1`)
- Tax year and source workbook filename
- Load timestamp and loaded-by value
- Optional notes

A new code is required for every successful load, including a corrected workbook from the same tax year.

### `active_data_snapshot`

Stores a singleton pointer to the snapshot represented by the generated tables. API queries use the active snapshot context, including when applying suppressions.

### `association_suppressions`

Records administrative decisions to hide particular generated associations from normal read responses. Each record is tied to a snapshot and retains:

- Association ID and both entity IDs/names
- Reason, created-by value, and timestamp
- Restoration timestamp, restored-by value, and reason when applicable

Suppression does **not** delete the association or its evidence. Restoration preserves the earlier suppression record as audit history.

**Important historical-data limitation:** `data_snapshots` preserves the *history of loads*, not full historical copies of the six generated tables. After a successful refresh, only the new active dataset remains in those generated tables. Retain approved source workbooks and use separately managed backups if historical datasets must be recoverable.

## Database Accounts and Access

| Account | Responsibility |
|---|---|
| `treasury_api` | Read-only queries from regular API endpoints. |
| `treasury_admin_api` | Read access plus the limited writes needed for suppression and restoration. |
| `treasury_etl` | Replace generated-table rows and register/activate snapshots. |
| Database administrator | Provision accounts, manage grants, and create or change schema objects. |

The `treasury_etl` account requires:

- `SELECT` on the project database.
- `INSERT` and `DELETE` on all six generated tables.
- `INSERT` on `data_snapshots`.
- `INSERT` and `UPDATE` on `active_data_snapshot`.

The ETL account intentionally does **not** receive write access to `association_suppressions`, so an annual refresh cannot silently modify administrative decisions. Routine API and ETL operations should not use the MySQL root account.

## Validated 2025 Baseline

| Output | Count |
|---|---:|
| Parcels | 3,874 |
| Resolved entities | 4,954 |
| Parcel/entity roles | 12,050 |
| Entity associations | 299 |
| Association evidence | 477 |
| Entity occurrences | 12,067 |
| Directional association-view rows | 598 |

These values are specific to the validated 2025 development snapshot and are **not** expected to remain constant across tax years.

See [Installation & Setup](setup.md) for initial setup, [Annual Data Refresh](annual-refresh.md) for safe replacement, and [Testing & Validation](testing.md) for baseline checks.
