# Kalamazoo County Treasury Data Project

This project builds a data-processing and search system for Kalamazoo County Treasury delinquent-tax parcel data.

The system cleans and normalizes annual parcel exports, resolves repeated names into entities, identifies evidence-backed associations between people and organizations, stores the results in a normalized MySQL database, and exposes the data through a FastAPI API.

The project is designed to support Treasury staff research and future website integration.

> **Important:** Entity associations are research leads based on available parcel, name, role, and address evidence. They are not proof of legal ownership, beneficial ownership, control, or identity.

---

## Project Goals

The project is intended to:

- Convert annual Treasury parcel exports into a consistent relational data model.
- Resolve repeated owner, taxpayer, care-of, and tax-send-to names into entities.
- Preserve the underlying source occurrences used during entity resolution.
- Identify evidence-backed relationships between entities.
- Provide confidence levels and supporting evidence for associations.
- Allow Treasury staff to suppress incorrect associations without deleting the historical record.
- Provide a read API for integration with Treasury applications or a website.
- Support repeatable annual data refreshes without modifying pipeline code each year.
- Preserve snapshot history and protect the active dataset from partial or failed refreshes.

---

## Technology

The project currently uses:

- Python
- pandas
- MySQL
- SQLAlchemy
- PyMySQL
- FastAPI
- Pydantic
- python-dotenv
- pytest
- httpx

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## High-Level Architecture

```text
Annual Treasury Excel Export
          |
          v
      Extraction
          |
          v
   Cleaning / Normalization
          |
          v
    Entity Resolution
          |
          v
 Association Generation
          |
          v
    Pipeline Validation
          |
          v
        MySQL
          |
          v
       FastAPI
          |
          v
 Treasury Website / Other Clients
```

The ETL pipeline and API are separate components.

The ETL process periodically replaces the generated parcel/entity data in MySQL. The API reads the currently active dataset from MySQL and does not perform entity resolution itself.

---

## Main Project Structure

```text
kzoo_county_project/
│
├── api/
│   ├── __init__.py
│   ├── auth.py
│   ├── database.py
│   ├── admin_database.py
│   ├── main.py
│   ├── schemas.py
│   └── routers/
│       ├── __init__.py
│       ├── entities.py
│       ├── associations.py
│       └── admin.py
│
├── database/
    ├── create_schema.sql
    ├── admin_schema.sql
│   └── load_database.py
│
├── tests/
│   ├── admin/
│   ├── contract/
│   ├── etl/
│   └── snapshot_2025/
│
├── data_cleaning.py
├── entity_resolution.py
├── etl_pipeline.py
├── extraction.py
├── requirements.txt
├── .env.example
└── README.md
```

Additional SQL schema and development/audit files may also be present in the repository.

---

# Data Pipeline

The ETL pipeline performs four major stages:

1. Extraction
2. Cleaning and normalization
3. Entity resolution and association generation
4. Database validation and load

The annual pipeline is run through:

```bash
python etl_pipeline.py
```

with command-line arguments specifying the source workbook, tax year, and snapshot information.

---

## Entity Resolution

The entity-resolution process converts repeated source names into resolved entities while preserving the original source occurrences.

The process is intentionally conservative. Exact or strongly supported relationships are preferred over aggressive fuzzy matching.

The current pipeline produces:

- Entity occurrences
- Resolved entities
- Parcel/entity roles
- Association evidence
- Entity associations

Organization and person records may be merged when supported by deterministic evidence such as normalized names, addresses, parcel overlap, and explicitly defined resolution rules.

Ambiguous records are intentionally left separate when there is insufficient evidence to merge them safely.

---

## Association Confidence

Associations are generated from specific evidence rules such as:

- Same-parcel co-ownership
- Owner/person and organization relationships on the same parcel
- Taxpayer relationships
- Tax-send-to relationships
- Care-of relationships
- Shared owner addresses
- Shared taxpayer addresses

Each association receives a confidence level based on the strongest individual supporting evidence.

Current confidence levels are:

```text
High
Medium
Low
```

Confidence is **not a probability** and should not be interpreted as a percentage likelihood that one entity owns or controls another.

Supporting evidence remains available through the API so that users can understand why an association was created.

---

# Database

The generated dataset is stored in MySQL.

## Generated Tables

The annual ETL refresh replaces the contents of these tables:

```text
parcels
entities
parcel_entity_roles
entity_associations
association_evidence
entity_occurrences
```

The database also contains the directional association view:

```text
entity_association_neighbors
```

This view exposes both directions of each normalized association pair.

---

## Persistent Administrative Tables

The following tables are not cleared during annual ETL refreshes:

```text
data_snapshots
active_data_snapshot
association_suppressions
```

### `data_snapshots`

Stores the historical record of successful dataset loads.

Each snapshot contains information such as:

- Snapshot code
- Tax year
- Source filename
- Load timestamp
- Loaded-by value
- Optional notes

A snapshot code identifies one specific processed version of a dataset.

For example:

```text
2026-v1
2026-v2
```

Multiple snapshots may represent the same tax year if a corrected or revised dataset must be loaded.

Snapshot codes must not be reused.

### `active_data_snapshot`

Contains a single pointer identifying which snapshot is currently represented by the generated database tables.

### `association_suppressions`

Stores administrative decisions to hide associations that Treasury staff determine should not appear in normal search results.

Suppressions are snapshot-specific and preserve:

- Association ID
- Entity IDs
- Entity names
- Reason
- Created-by information
- Timestamp
- Restoration history

Suppressions are preserved as audit history rather than deleting association records.

---

# Initial Database Setup

For a new MySQL installation, initialize the project in this order:

1. Run `create_schema.sql` to create the generated-data tables and
   `entity_association_neighbors` view.
2. Run `admin_schema.sql` to create the persistent snapshot and
   administrative tables.
3. Create the least-privilege MySQL accounts described below.
4. Copy `.env.example` to `.env` and configure the required
   credentials and administrative API key.
5. Run the ETL pipeline to create and activate the initial data
   snapshot.
6. Start the FastAPI application and run the automated tests.

`create_schema.sql` defines data that is replaced by annual ETL
refreshes. `admin_schema.sql` defines persistent administrative
history and must not be recreated as part of a normal annual refresh.

---

# Database Accounts

The system uses separate MySQL accounts for different responsibilities.

| Account | Purpose |
| --- | --- |
| `treasury_api` | Read-only access used by normal API endpoints |
| `treasury_admin_api` | Read access plus suppression/restoration administration |
| `treasury_etl` | Annual generated-data refresh and snapshot activation |
| Database administrator/root | Schema and account administration only |

Routine application or ETL activity should not use the MySQL root account.

---

## ETL Account Permissions

The `treasury_etl` account requires:

- `SELECT` access to the Treasury database
- `INSERT` and `DELETE` on the six generated tables
- `INSERT` on `data_snapshots`
- `INSERT` and `UPDATE` on `active_data_snapshot`

It intentionally does **not** have write access to:

```text
association_suppressions
```

This prevents an annual data refresh from changing administrative suppression decisions.

---

# Environment Configuration

Local secrets and database credentials belong in:

```text
.env
```

The `.env` file must not be committed to source control.

Use `.env.example` as the configuration template.

Example:

```dotenv
TREASURY_DB_HOST=localhost
TREASURY_DB_PORT=3306
TREASURY_DB_NAME=kalamazoo_county_treasury

# Read-only API account
TREASURY_DB_USER=treasury_api
TREASURY_DB_PASSWORD=

# Administrative API account
TREASURY_ADMIN_DB_USER=treasury_admin_api
TREASURY_ADMIN_DB_PASSWORD=

# Administrative API authentication
TREASURY_ADMIN_API_KEY=

# ETL refresh account
TREASURY_ETL_DB_USER=treasury_etl
TREASURY_ETL_DB_PASSWORD=
```

Never place real passwords or API keys in `.env.example`.

---

# Running the API

For local development:

```bash
python -m uvicorn api.main:app --reload --env-file .env
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation is available during development at:

```text
http://127.0.0.1:8000/docs
```

---

# Read API Endpoints

## Health Check

```http
GET /api/health
```

Confirms that the API can connect to MySQL and that an active data snapshot exists.

---

## Search Entities

```http
GET /api/entities/search?q=<search term>
```

Searches resolved entities by name.

---

## Get Entity

```http
GET /api/entities/{entity_id}
```

Returns information about one resolved entity.

---

## Get Entity Parcels

```http
GET /api/entities/{entity_id}/parcels
```

Returns parcels associated with the entity and the entity's recorded roles.

---

## Get Entity Associations

```http
GET /api/entities/{entity_id}/associations
```

Returns non-suppressed associations for the entity.

Association results include information such as confidence and supporting evidence counts.

---

## Get Association Evidence

```http
GET /api/associations/{association_id}/evidence
```

Returns the evidence supporting an association.

A currently suppressed association is not returned through the normal read endpoint.

---

# Administrative API

Administrative endpoints require the HTTP header:

```text
X-Admin-Key
```

The expected value comes from:

```text
TREASURY_ADMIN_API_KEY
```

The current shared API-key mechanism is intended for development
or a tightly controlled internal deployment. The admin key must
never be embedded in browser-side code.

A full production deployment should integrate with County
authentication infrastructure so administrative actions can be
attributed to authenticated staff rather than solely to a shared key
and caller-supplied `created_by` / `revoked_by` values.

---

## Suppress an Association

```http
POST /api/admin/associations/{association_id}/suppress
```

Example request:

```json
{
    "reason": "Association reviewed and determined to be incorrect.",
    "created_by": "Treasury Staff"
}
```

Suppressing an association removes it from normal association search results while preserving an audit record.

---

## Restore an Association

```http
POST /api/admin/associations/{association_id}/restore
```

Example request:

```json
{
    "revoked_by": "Treasury Staff",
    "revocation_reason": "Association reviewed again and restored."
}
```

Restoration does not delete the original suppression record.

---

## View Suppressions

Active suppressions:

```http
GET /api/admin/association-suppressions
```

Include restored suppression history:

```http
GET /api/admin/association-suppressions?include_restored=true
```

---

# Annual Data Refresh

The ETL pipeline is designed so that a new annual Treasury workbook can be processed without changing Python source code.

View the available options with:

```bash
python etl_pipeline.py --help
```

The main arguments are:

```text
--input
--sheet
--year
--snapshot-code
--loaded-by
--notes
--validate-only
```

---

## Step 1: Validate the New Dataset

Always run a validation-only pass first.

Example:

```bash
python etl_pipeline.py \
    --input "2026 Roll - Parcels Export.xlsx" \
    --sheet "Only Delinquent Parcels" \
    --year 2026 \
    --validate-only
```

On Windows PowerShell:

```powershell
python etl_pipeline.py `
    --input "2026 Roll - Parcels Export.xlsx" `
    --sheet "Only Delinquent Parcels" `
    --year 2026 `
    --validate-only
```

A validation-only run performs extraction, cleaning, and entity resolution but does **not** call the database loader and does not modify MySQL.

A successful validation-only run ends with:

```text
VALIDATION-ONLY RUN COMPLETED
NO DATABASE CHANGES WERE MADE
```

Review the pipeline output and any audit results before performing the real refresh.

---

## Step 2: Perform the Annual Refresh

After validation succeeds, run the pipeline with a unique snapshot code.

Example:

```bash
python etl_pipeline.py \
    --input "2026 Roll - Parcels Export.xlsx" \
    --sheet "Only Delinquent Parcels" \
    --year 2026 \
    --snapshot-code "2026-v1" \
    --loaded-by "Treasury Staff" \
    --notes "Initial validated 2026 delinquent parcel snapshot."
```

PowerShell:

```powershell
python etl_pipeline.py `
    --input "2026 Roll - Parcels Export.xlsx" `
    --sheet "Only Delinquent Parcels" `
    --year 2026 `
    --snapshot-code "2026-v1" `
    --loaded-by "Treasury Staff" `
    --notes "Initial validated 2026 delinquent parcel snapshot."
```

The source filename stored in the snapshot record is derived automatically from the `--input` filename.

---

## Snapshot Codes

A snapshot represents one specific processed version of a dataset.

Recommended naming:

```text
2026-v1
2026-v2
2027-v1
```

For example:

```text
2026-v1
```

could represent the initial 2026 load.

If a corrected 2026 file is later supplied, it should receive a new snapshot code such as:

```text
2026-v2
```

Do not reuse an existing snapshot code.

---

# Transactional Refresh Safety

Database replacement occurs inside a single SQLAlchemy/MySQL transaction.

The refresh sequence is:

```text
Validate pipeline outputs
        |
        v
Open database transaction
        |
        v
Validate database schema
        |
        v
Clear generated-table rows
        |
        v
Load new generated data
        |
        v
Validate database row counts
        |
        v
Register snapshot
        |
        v
Activate snapshot
        |
        v
Commit
```

If any operation fails before the transaction commits, the generated-data refresh is rolled back.

This protects the currently active dataset from a partially completed annual refresh.

The generated tables use a transactional MySQL storage engine so that the DELETE and INSERT operations can participate in the rollback.

Snapshot registration and activation occur only after the newly loaded database has passed validation.

---

# 2025 Validated Baseline

The current validated 2025 project snapshot contains:

| Output | Rows |
| --- | ---: |
| Parcels | 3,874 |
| Resolved entities | 4,954 |
| Parcel/entity roles | 12,050 |
| Entity associations | 299 |
| Association evidence | 477 |
| Entity occurrences | 12,067 |
| Directional association view | 598 |

These values are used by the 2025 snapshot regression tests.

Future tax years are not expected to match these counts.

---

# Testing

Run the entire automated test suite with:

```bash
python -m pytest -v
```

The current suite contains **67 passing tests** when run
against the validated 2025 development snapshot.

Tests are organized by purpose:

```text
tests/
├── admin/
│   └── Administrative suppression and restoration behavior
│
├── contract/
│   └── Read API contract behavior
│
├── etl/
│   ├── Data-cleaning validation tests
│   ├── ETL configuration tests
│   ├── Snapshot registration tests
│   └── Annual-refresh CLI tests
│
└── snapshot_2025/
    └── Regression tests for the validated 2025 dataset
```

The ETL unit tests do not modify the live Treasury database.

The read-API, administrative-API, and validated-snapshot tests
are integration tests and require access to a configured Treasury
MySQL database.

Administrative API tests execute real suppression/restoration SQL
inside rollback-only test transactions so that test records are not
persisted.

The `snapshot_2025` regression suite applies only to the exact
validated 2025 baseline snapshot and is skipped when another snapshot
is active.

Transactional rollback behavior has also been manually verified.
Generated-table replacement, database validation, snapshot
registration, and snapshot activation occur within one transaction,
so a failure before commit does not leave a partially refreshed
active dataset.

Duplicate snapshot codes are now rejected during preflight before
generated tables are cleared.

---

## Running Specific Test Groups

Read API contract tests:

```bash
python -m pytest tests/contract -v
```

Administrative API tests:

```bash
python -m pytest tests/admin -v
```

2025 regression tests:

```bash
python -m pytest tests/snapshot_2025 -v
```

ETL and snapshot lifecycle tests:

```bash
python -m pytest tests/etl -v
```

---

# Data Interpretation and Limitations

This system is designed to assist Treasury staff with research and prioritization.

Entity resolution is based on the information available in the annual parcel export and deterministic matching rules.

An association may indicate that two entities:

- appear on the same parcel,
- share a mailing address,
- appear in related owner/taxpayer roles,
- or meet another defined evidence rule.

An association does **not** by itself establish:

- beneficial ownership,
- legal control,
- common identity,
- fraud,
- foreclosure risk,
- or any other legal conclusion.

Important decisions should be corroborated using appropriate authoritative sources.

---

# Development Principles

The project follows several guiding principles:

### Conservative Entity Resolution

Prefer leaving ambiguous records separate rather than incorrectly combining unrelated people or organizations.

### Explainability

Associations retain the evidence rules and source records that caused them to be generated.

### Auditability

Administrative suppression decisions and restorations are retained rather than silently deleting history.

### Least-Privilege Database Access

API, administrative, ETL, and schema-management responsibilities use separate database permission levels.

### Safe Annual Refreshes

Annual data replacement is validated before activation and protected by database transactions.

### Reproducibility

The same ETL code can process future annual datasets using command-line configuration rather than source-code edits.

---

# Current Status

The project currently includes:

- Annual Excel extraction
- Data cleaning and normalization
- Entity occurrence creation
- Conservative entity resolution
- Parcel/entity role generation
- Evidence-backed entity associations
- Normalized MySQL storage
- Directional association view
- Read-only FastAPI endpoints
- Administrative association suppression and restoration
- Snapshot history and active-snapshot tracking
- Reusable annual-refresh CLI
- Validation-only annual refresh mode
- Dedicated least-privilege ETL database account
- Transactional refresh rollback protection
- Automated API, regression, administrative, ETL, and snapshot tests

The current development dataset is the validated 2025 Treasury delinquent-parcel snapshot.

---

# Future Work

Potential next steps include:

- Production deployment and County infrastructure integration
- Final authentication/authorization integration
- Website integration
- Additional administrative tooling
- Additional external-source corroboration for entity research
- Further annual-refresh operational documentation
- Disposable database integration tests
- Long-term monitoring and maintenance procedures