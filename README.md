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

Future work will include:

- Relational database implementation
- Entity resolution improvements
- API integration
- Predictive modeling

---

## Notes

To protect taxpayer privacy, source datasets provided by Kalamazoo County are **not included** in this repository. Any example data used for development or demonstration purposes is synthetic and does not represent actual county records.
