# System Architecture

[← Back to project README](../README.md)

## Purpose

The Kalamazoo County Treasury project converts an annual delinquent-property-tax parcel export into a searchable collection of parcels, resolved entities, recorded roles, and evidence-backed associations between people and organizations.

The system is intended to support Treasury research. An association is a **research lead**, not proof of legal ownership, beneficial ownership, control, identity, fraud, or foreclosure risk.

## High-Level Data Flow

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
Treasury Website / Other Client
```

The **ETL pipeline** processes a workbook and updates the database. The **FastAPI application** reads the currently active dataset; it does not perform entity resolution during API requests. Production website integration is a separate deployment activity.

## Main Components

| Component | Purpose |
|---|---|
| `extraction.py` | Read the selected Excel worksheet and extract parcel, name, address, role, and valuation fields. |
| `data_cleaning.py` | Standardize and validate the extracted parcel data. |
| `entity_resolution.py` | Build traceable occurrences, resolved entities, parcel roles, association evidence, and final associations. |
| `etl_pipeline.py` | Coordinate extraction, cleaning, resolution, validation, and optional MySQL loading. |
| `database/load_database.py` | Validate outputs and perform a transactional database refresh. |
| `api/` | Expose read endpoints and protected administrative endpoints. |
| `tests/` | Verify the ETL, API behavior, administrative operations, and validated 2025 dataset. |
| `notebooks/` | Present exploratory analysis and an entity-resolution/association overview. |

## Entity Resolution

The entity-resolution process deliberately distinguishes **source occurrences** from **resolved entities**. A name appearing on multiple parcels or in multiple fields may correspond to a single entity, but the system retains the source observations used to reach that result.

The pipeline produces the following outputs:

1. **Entity occurrences** — source name observations, their roles, and source lineage.
2. **Resolved entities** — canonical people, organizations, and other supported entity types, using conservative deterministic matching rules.
3. **Parcel/entity roles** — unique combinations of parcel, entity, and recorded role.
4. **Association evidence** — individual, rule-specific reasons to investigate a Person–Organization pair.
5. **Entity associations** — normalized entity pairs summarizing their strongest supporting evidence.

Names and addresses are normalized where the rules provide sufficient support. Ambiguous records are intentionally left separate rather than merged through unrestricted fuzzy matching. A shared name or address alone should not be treated as proof that records represent the same person or organization.

## Association Generation

Associations between a person and an organization are based on explicit evidence rules. The current implementation includes eight rules:

| Strength | Evidence rule | General meaning |
|---|---|---|
| High | `SAME_PARCEL_CO_OWNER` | Person and organization appear as owners on the same parcel. |
| High | `SAME_PARCEL_ORG_OWNER_PERSON_TAXPAYER` | Organization is owner; person is taxpayer on the same parcel. |
| High | `SAME_PARCEL_ORG_TAXPAYER_PERSON_OWNER` | Organization is taxpayer; person is owner on the same parcel. |
| Medium | `SAME_PARCEL_ORG_OWNER_PERSON_TAX_SEND_TO` | Organization is owner; person is tax-send-to on the same parcel. |
| Medium | `SAME_PARCEL_ORG_TAX_SEND_TO_PERSON_OWNER` | Organization is tax-send-to; person is owner on the same parcel. |
| Medium | `SHARED_OWNER_ADDRESS` | Person and organization owner records share an owner mailing address across different parcels. |
| Medium | `SHARED_TAXPAYER_ADDRESS` | Person and organization owner records share a taxpayer mailing address across different parcels. |
| Low | `SAME_PARCEL_ORG_OWNER_PERSON_OWNER_CARE_OF` | Organization is owner; person appears in the owner-care-of role on the same parcel. |

The association's `High`, `Medium`, or `Low` category is the **strongest individual evidence strength** present for that pair. Multiple weaker signals do **not** add up to a higher category, and the category is **not a probability**.

Individual evidence events remain available through `association_evidence` and the API, including supporting roles, parcels where applicable, and shared addresses where applicable. The database stores each normalized entity pair once and exposes both lookup directions through the `entity_association_neighbors` view.

## Design Principles

- **Conservative matching:** Prefer unmatched ambiguous records over potentially incorrect identity merges.
- **Explainability:** Retain source occurrences and the explicit rules behind every association.
- **Auditability:** Preserve association suppression and restoration history.
- **Least privilege:** Separate read API, administrative API, ETL, and schema-management database permissions.
- **Safe refreshes:** Validate before loading, then replace generated tables within a single transaction.
- **Reusability:** Use annual-refresh command-line arguments rather than yearly source-code edits, provided the input format remains compatible.

## Interpretation and Limitations

The system uses the information present in the Treasury export. Recorded names, mailing addresses, and roles may be incomplete, inconsistent, or outdated. Associations help prioritize follow-up research and should be corroborated using authoritative records before consequential decisions.

For implementation details, see [Database Documentation](database.md), [API Reference](api-reference.md), and [Annual Data Refresh](annual-refresh.md).
