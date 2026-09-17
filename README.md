# Kalamazoo County Property Data Project

## Overview

This repository contains work completed as part of a data science project in collaboration with the Kalamazoo County Treasurer's Office and Western Michigan University.

The long-term goal of the project is to support the development of predictive models that identify property owners at risk of property tax foreclosure before foreclosure occurs. The current phase of the project focuses on designing and building a relational database that accurately links property owners, taxpayers, organizations, and parcels across Kalamazoo County.

Because ownership information may appear under multiple names or legal entities (e.g., LLCs and trusts), the project also explores techniques for entity resolution and record linkage.

---

## Project Objectives

- Explore and profile county parcel and taxpayer datasets
- Clean and standardize owner, taxpayer, and address information
- Normalize property records into a relational database
- Identify duplicate and related entities
- Develop repeatable ETL workflows using Python and SQL
- Prepare data for future predictive modeling and API integration

---

## Technologies

- Python
- Pandas
- Jupyter Notebook
- MySQL
- SQL
- Git/GitHub

---

## Repository Structure

```
├── data/
│   ├── raw/                 # Original source data (not tracked)
│   ├── processed/           # Cleaned datasets (optional)
│
├── notebooks/
│   ├── data_profiling.ipynb
│
├── sql/
│   ├── schema.sql
│   ├── staging_tables.sql
│
├── src/
│   ├── cleaning.py
│   ├── entity_matching.py
│   ├── etl.py
│
├── docs/
│   ├── database_design.md
│   ├── data_dictionary.md
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Workflow

1. Load raw parcel and taxpayer data.
2. Clean and standardize names and addresses.
3. Profile the data to identify quality issues and ownership patterns.
4. Perform entity matching and record linkage.
5. Load cleaned data into a normalized MySQL database.
6. Support future API development and predictive analytics.

---

## Current Status

Current work includes:

- Data exploration
- Data profiling
- Address and entity normalization
- SQL schema planning
- ETL pipeline development
- Relational database implementation
- Entity resolution improvements
- API integration

Future work will include:
- Predictive modeling

---

## API

The project includes a FastAPI application that provides read access to the
entity-resolution and parcel-association data stored in MySQL.

The API is intended to act as an interface between the Kalamazoo County
Treasury website and the underlying MySQL database. Entity resolution and
association generation are performed by the ETL pipeline; the API retrieves
the resulting data but does not perform entity resolution itself.

### Configuration

Database connection settings are supplied through environment variables.
The repository includes `.env.example` as a configuration template.

Create a local `.env` file with values similar to:

```text
TREASURY_DB_HOST=localhost
TREASURY_DB_PORT=3306
TREASURY_DB_NAME=kalamazoo_county_treasury
TREASURY_DB_USER=treasury_api
TREASURY_DB_PASSWORD=your_password
```

The .env file contains local credentials and should not be committed to Git.

Installing Dependencies

Install the project's Python dependencies with:

python -m pip install -r requirements.txt
Starting the API

From the project root, run:

python -m uvicorn api.main:app --reload --env-file .env

During local development, the API is available at:

http://127.0.0.1:8000

Interactive FastAPI documentation is available at:

http://127.0.0.1:8000/docs

Current Read-Only Endpoints:
- GET /api/health
- GET /api/entities/search?q={name}
- GET /api/entities/{entity_id}
- GET /api/entities/{entity_id}/parcels
- GET /api/entities/{entity_id}/associations
- GET /api/associations/{association_id}/evidence

Association confidence represents the strength of the strongest evidence rule
supporting an association. It should not be interpreted as a probability of
ownership or control.

Running API Tests

The API test suite can be run from the project root with:

python -m pytest -v

The current integration tests connect to the configured MySQL database and
therefore require the database to be available and populated before testing.

## Notes

To protect taxpayer privacy, source datasets provided by Kalamazoo County are **not included** in this repository. Any example data used for development or demonstration purposes is synthetic and does not represent actual county records.
