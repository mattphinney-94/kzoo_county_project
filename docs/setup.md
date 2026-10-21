# Installation & Setup

[← Back to project README](../README.md)

## Prerequisites

- **Python 3.12** (the development environment used to verify the project).
- A compatible **MySQL 8.0+** server. The SQL schema uses the `utf8mb4_0900_ai_ci` collation and enforced `CHECK` constraints; use a MySQL version supporting these features.
- The project source code and the approved annual Treasury Excel workbook.
- Permissions to create the initial schema and provision separate MySQL users.

The Python dependencies are listed in [`requirements.txt`](../requirements.txt); [`requirements-lock.txt`](../requirements-lock.txt) records the pinned development dependencies.

## 1. Create a Virtual Environment

From the repository root, in Windows PowerShell:

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

On macOS/Linux, use the available Python 3.12 executable, create a virtual environment, and install `requirements.txt` with that environment's Python and pip.

The project uses `pandas`, `openpyxl`, `SQLAlchemy`, `PyMySQL`, `FastAPI`, `uvicorn`, `pydantic`, `python-dotenv`, `pytest`, and `httpx`.

## 2. Create the MySQL Schema

Connect to MySQL with an account authorized to create databases, tables, and views. From the repository root, you can open the MySQL command-line client:

```powershell
mysql -u root -p
```

At the `mysql>` prompt, run:

```sql
SOURCE database/create_schema.sql;
SOURCE database/admin_schema.sql;
```

If the client cannot locate relative paths, use their absolute paths or open the SQL files in a MySQL-compatible SQL editor such as DBeaver.

- `create_schema.sql` creates the generated-data tables and `entity_association_neighbors` view.
- `admin_schema.sql` creates the persistent `data_snapshots`, `active_data_snapshot`, and `association_suppressions` tables.

**Run these scripts for a fresh installation, not as part of an annual data refresh.** The generated-data schema uses ordinary `CREATE TABLE` statements; attempting to recreate it in a populated database is not the refresh procedure.

## 3. Provision Database Accounts

Create dedicated MySQL users for these responsibilities:

| Account | Required access |
|---|---|
| `treasury_api` | Read-only access for regular API requests. |
| `treasury_admin_api` | Read access and limited suppression/restoration administration. |
| `treasury_etl` | Read access; insert/delete on generated tables; insert snapshots; insert/update active snapshot. |
| Administrator | Initial schema creation and account management only. |

Detailed permission guidance is in [Database Documentation](database.md). The repository's schema scripts define database objects; **the administrator must separately provision the users and grants**. Do not configure routine application connections to use `root`.

## 4. Configure Environment Variables

Copy the template in the repository root:

```powershell
Copy-Item .env.example .env
```

Edit `.env` locally:

```dotenv
TREASURY_DB_HOST=localhost
TREASURY_DB_PORT=3306
TREASURY_DB_NAME=kalamazoo_county_treasury

# Read-only API account
TREASURY_DB_USER=treasury_api
TREASURY_DB_PASSWORD=YOUR_READ_ONLY_PASSWORD

# Administrative API account
TREASURY_ADMIN_DB_USER=treasury_admin_api
TREASURY_ADMIN_DB_PASSWORD=YOUR_ADMIN_PASSWORD

# Development/internal administrative API authentication
TREASURY_ADMIN_API_KEY=YOUR_STRONG_RANDOM_ADMIN_KEY

# ETL refresh account
TREASURY_ETL_DB_USER=treasury_etl
TREASURY_ETL_DB_PASSWORD=YOUR_ETL_PASSWORD
```

Replace the placeholders with actual credentials appropriate to the environment. **Never commit `.env`, database passwords, or API keys to Git.** `.env.example` must contain only blank or non-secret example values.

The current admin key is suitable only for development or a tightly controlled internal environment. A production deployment should use County-managed authentication, authorization, and staff attribution; never place this key in browser-side code.

## 5. Validate the Source Workbook

The 2025 development workbook is named `2025 Roll - Parcels Export.xlsx`. The production pipeline defaults to the worksheet **`Only Delinquent Parcels`**, not `All Parcels`.

From the repository root, run a validation-only ETL pass (this does not modify MySQL):

```powershell
& ".\.venv\Scripts\python.exe" etl_pipeline.py `
  --input "2025 Roll - Parcels Export.xlsx" `
  --sheet "Only Delinquent Parcels" `
  --year 2025 `
  --validate-only
```

Review the output and resolve any validation errors before loading data. For later tax years, replace the input path and year with the appropriate values. The ETL input may be an absolute path to a secured County location; the workbook does not need to be stored in the repository.

## 6. Load the Initial Snapshot

After validation, use a unique snapshot code. For a **new, empty** database populated with the validated 2025 workbook, the historical test baseline expects the code `2025`:

```powershell
& ".\.venv\Scripts\python.exe" etl_pipeline.py `
  --input "2025 Roll - Parcels Export.xlsx" `
  --sheet "Only Delinquent Parcels" `
  --year 2025 `
  --snapshot-code "2025" `
  --loaded-by "Treasury ETL" `
  --notes "Validated 2025 development baseline."
```

**Do not run this real-load command against an existing active County database.** A successful load replaces the generated tables. See [Annual Data Refresh](annual-refresh.md) before loading any updated dataset.

## 7. Start FastAPI

From the repository root:

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn api.main:app --reload --env-file .env
```

- API: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`

The health endpoint requires database connectivity **and** an active snapshot. Stop the local development server with `Ctrl+C`.

`--reload` and local Swagger UI are development conveniences, not a production deployment configuration.

## 8. Run Tests

The ETL tests can be run without a live Treasury database:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/etl -v
```

The full suite also includes database-dependent integration and regression tests:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -v
```

See [Testing & Validation](testing.md) for prerequisites and expected 2025 baseline results.
