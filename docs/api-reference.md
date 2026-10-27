# API Reference

[← Back to project README](../README.md)

## Overview

The project exposes a **FastAPI** REST interface for searching resolved entities, retrieving associated parcels, reviewing entity associations, and inspecting the evidence supporting an association. Separate administrative endpoints allow authorized staff to suppress or restore associations without deleting the original data.

For local development, start the API using the command in [Installation & Setup](setup.md) and open the interactive OpenAPI/Swagger documentation at:

```text
http://127.0.0.1:8000/docs
```

The URL above is local to the machine running the API; it is **not** a public hosted service.

## Read-Only Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check MySQL connectivity and confirm an active snapshot exists. |
| `GET` | `/api/entities/search?q={term}` | Search canonical names and source-name variants. |
| `GET` | `/api/entities/{entity_id}` | Retrieve an entity's canonical details. |
| `GET` | `/api/entities/{entity_id}/parcels` | Retrieve distinct parcels and the entity's recorded roles on each parcel. |
| `GET` | `/api/entities/{entity_id}/associations` | Retrieve non-suppressed associations for an entity. |
| `GET` | `/api/associations/{association_id}/evidence` | Retrieve individual evidence events for a non-suppressed association. |

### Health Check

```http
GET /api/health
```

Returns `status: healthy` and `database: connected` when the database connection works and an active snapshot is configured. Otherwise, the endpoint can return HTTP `503`.

### Search Entities

```http
GET /api/entities/search?q=graham
```

The `q` parameter is required and accepts a name or partial name. The optional `limit` parameter defaults to `25` and accepts values from `1` through `100`.

Searches include canonical entity names and source-name variants recorded in `entity_occurrences`. Results contain one row per resolved entity, including identifying fields and `occurrence_count`.

**Flexible name search:** The API first runs its existing literal substring search. For searches containing multiple words—or single-word searches with no substring matches—it also checks order-independent name matches, a short curated nickname list (such as Will/Bill → William), and small spelling errors in name tokens. Existing literal substring matches rank first. Similar-looking names are **candidate search results**, not automatically merged people or organizations. All existing entity IDs, addresses, and evidence remain unchanged.

Examples for the validated 2025 data include `William Graham`, `William D Graham`, `Graham William D`, `Will Graham`, and `Will Grahm`. For ambiguous names, compare addresses, roles, and source evidence before drawing conclusions. Approximate search does not imply an association confidence category.

### Get Entity Details

```http
GET /api/entities/1719
```

Returns the canonical name, entity type, canonical address where available, classification information, and source occurrence count.

### Get an Entity's Parcels

```http
GET /api/entities/1719/parcels
```

Returns one entry per distinct parcel, its property/valuation fields where available, and a list of the entity's recorded roles on that parcel. An entity may have more than one role on a parcel.

### Get an Entity's Associations

```http
GET /api/entities/1719/associations
```

Returns associated entity IDs, names, types, `association_confidence`, `evidence_count`, and `evidence_rule_count`. An association suppressed for the active snapshot is omitted.

### Get Association Evidence

```http
GET /api/associations/173/evidence
```

Returns supporting rule-level evidence for one association, which may include evidence strength, parcel references, recorded roles, shared address, and address type.

**2025 example:** In the validated 2025 snapshot, entity `1719` is `GRAHAM, WILLIAM D` (six parcels). Association `173` links that entity with `THE COPPER CREEK TRUST` and has 20 evidence events covering five distinct rules. These IDs and counts belong to the validated 2025 baseline and may change after a future ETL refresh.

## Administrative Endpoints

Administrative routes require the `X-Admin-Key` request header, with the value configured locally using `TREASURY_ADMIN_API_KEY`. These routes use the separate administrative database account.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/admin/associations/{association_id}/suppress` | Hide an association from normal read results while preserving evidence and an audit record. |
| `POST` | `/api/admin/associations/{association_id}/restore` | Restore a previously suppressed association and retain suppression history. |
| `GET` | `/api/admin/association-suppressions` | List active suppressions for the active snapshot. |

### Suppress an Association

```http
POST /api/admin/associations/173/suppress
X-Admin-Key: YOUR_ADMIN_KEY
Content-Type: application/json
```

```json
{
  "reason": "Association reviewed and determined to be incorrect.",
  "created_by": "Treasury Staff"
}
```

On success, the endpoint creates a snapshot-specific suppression record (HTTP `201`). The underlying association and its evidence remain in the generated tables.

### Restore an Association

```http
POST /api/admin/associations/173/restore
X-Admin-Key: YOUR_ADMIN_KEY
Content-Type: application/json
```

```json
{
  "revoked_by": "Treasury Staff",
  "revocation_reason": "Association reviewed again and restored."
}
```

Restoration does not delete the original suppression record.

### List Suppressions

Active suppressions:

```http
GET /api/admin/association-suppressions
```

Include previously restored suppression records:

```http
GET /api/admin/association-suppressions?include_restored=true
```

The listing applies to the **currently active snapshot**.

## Security and Interpretation

- The shared `X-Admin-Key` mechanism is intended for development or a tightly controlled internal deployment; **never expose the key in frontend/browser code**.
- The `created_by` and `revoked_by` fields are supplied by callers, so the development key alone does not provide verified individual staff attribution.
- A County production deployment should integrate County-managed authentication/authorization, secure hosting, network controls, and staff attribution.
- `High`, `Medium`, and `Low` are qualitative evidence strengths, **not ownership probabilities**.
- Association results are research leads and are not proof of ownership, control, or identity.
- The examples above refer to the validated 2025 development snapshot and must not be assumed stable across refreshes.

For schema details, see [Database Documentation](database.md). For the administrative audit model and persistence rules, see [Annual Data Refresh](annual-refresh.md).
