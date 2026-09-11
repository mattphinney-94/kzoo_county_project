-- ==========================================================
-- KALAMAZOO COUNTY PARCEL / ENTITY ASSOCIATION DATABASE
-- V1 RELATIONAL SCHEMA
-- ==========================================================

CREATE DATABASE IF NOT EXISTS kalamazoo_county_treasury;

USE kalamazoo_county_treasury;

-- ==========================================================
-- 1. PARCELS
-- One row per delinquent parcel
-- ==========================================================

CREATE TABLE parcels (
    parcel_number VARCHAR(32) NOT NULL,

    property_address VARCHAR(255) NULL,

    principal_residence_exemption_percentage TINYINT UNSIGNED NULL,

    property_class VARCHAR(64) NULL,

    tax_value INT UNSIGNED NULL,
    assessed_value INT UNSIGNED NULL,
    state_equalized_value INT UNSIGNED NULL,

    PRIMARY KEY (
        parcel_number
    ),

    INDEX idx_parcels_property_address (
        property_address
    ),

    INDEX idx_parcels_property_class (
        property_class
    ),

    CHECK (
        principal_residence_exemption_percentage IS NULL
        OR
        principal_residence_exemption_percentage BETWEEN 0 AND 100
    )
);

-- ==========================================================
-- 2. ENTITIES
-- One row per resolved entity
-- ==========================================================

CREATE TABLE entities (
    entity_id BIGINT UNSIGNED NOT NULL,

    canonical_name VARCHAR(255) NOT NULL,

    entity_type VARCHAR(32) NOT NULL,

    canonical_address VARCHAR(255) NULL,

    organization_type VARCHAR(64) NULL,

    organization_classification_confidence VARCHAR(16) NULL,

    occurrence_count INT UNSIGNED NOT NULL,

    PRIMARY KEY (
        entity_id
    ),

    INDEX idx_entities_canonical_name (
        canonical_name
    ),

    INDEX idx_entities_entity_type (
        entity_type
    ),

    CHECK (
        entity_type IN (
            'Person',
            'Organization',
            'Joint',
            'Unknown'
        )
    ),

    CHECK (
        organization_classification_confidence IS NULL
        OR
        organization_classification_confidence IN (
            'High',
            'Medium',
            'Low'
        )
    ),

    CHECK (
        occurrence_count >= 1
    )
);

-- ==========================================================
-- 3. PARCEL ENTITY ROLES
-- Grain: parcel_number + entity_id + role
-- ==========================================================

CREATE TABLE parcel_entity_roles (
    parcel_number VARCHAR(32) NOT NULL,

    entity_id BIGINT UNSIGNED NOT NULL,

    role VARCHAR(32) NOT NULL,

    PRIMARY KEY (
        parcel_number,
        entity_id,
        role
    ),

    CONSTRAINT fk_per_parcel
        FOREIGN KEY (
            parcel_number
        )
        REFERENCES parcels (
            parcel_number
        ),

    CONSTRAINT fk_per_entity
        FOREIGN KEY (
            entity_id
        )
        REFERENCES entities (
            entity_id
        ),

    INDEX idx_per_entity_role_parcel (
        entity_id,
        role,
        parcel_number
    ),

    INDEX idx_per_role (
        role
    ),

    CHECK (
        role IN (
            'Owner',
            'Owner Care Of',
            'Taxpayer',
            'Taxpayer Care Of',
            'Tax Send To'
        )
    )
);

-- ==========================================================
-- 4. ENTITY ASSOCIATIONS
-- Stage 6
-- One row per normalized entity pair
-- ==========================================================

CREATE TABLE entity_associations (
    association_id BIGINT UNSIGNED NOT NULL,

    entity_id_a BIGINT UNSIGNED NOT NULL,
    entity_id_b BIGINT UNSIGNED NOT NULL,

    association_confidence VARCHAR(16) NOT NULL,

    evidence_count INT UNSIGNED NOT NULL,
    evidence_rule_count INT UNSIGNED NOT NULL,

    PRIMARY KEY (
        association_id
    ),

    UNIQUE KEY uq_entity_association_pair (
        entity_id_a,
        entity_id_b
    ),

    CONSTRAINT fk_entity_association_a
        FOREIGN KEY (
            entity_id_a
        )
        REFERENCES entities (
            entity_id
        ),

    CONSTRAINT fk_entity_association_b
        FOREIGN KEY (
            entity_id_b
        )
        REFERENCES entities (
            entity_id
        ),

    INDEX idx_entity_association_b (
        entity_id_b
    ),

    INDEX idx_entity_association_confidence (
        association_confidence
    ),

    CHECK (
        entity_id_a < entity_id_b
    ),

    CHECK (
        association_confidence IN (
            'High',
            'Medium',
            'Low'
        )
    ),

    CHECK (
        evidence_count >= 1
    ),

    CHECK (
        evidence_rule_count >= 1
    ),

    CHECK (
        evidence_rule_count <= evidence_count
    )
);

-- ==========================================================
-- 5. ASSOCIATION EVIDENCE
-- Stage 5
-- One row per evidence event
-- ==========================================================

CREATE TABLE association_evidence (
    evidence_id BIGINT UNSIGNED NOT NULL,

    entity_id_a BIGINT UNSIGNED NOT NULL,
    entity_id_b BIGINT UNSIGNED NOT NULL,

    evidence_rule VARCHAR(96) NOT NULL,

    evidence_strength VARCHAR(16) NOT NULL,

    parcel_number_a VARCHAR(32) NULL,
    parcel_number_b VARCHAR(32) NULL,

    role_a VARCHAR(32) NOT NULL,
    role_b VARCHAR(32) NOT NULL,

    shared_address VARCHAR(255) NULL,

    address_type VARCHAR(32) NULL,

    PRIMARY KEY (
        evidence_id
    ),

    CONSTRAINT fk_evidence_entity_a
        FOREIGN KEY (
            entity_id_a
        )
        REFERENCES entities (
            entity_id
        ),

    CONSTRAINT fk_evidence_entity_b
        FOREIGN KEY (
            entity_id_b
        )
        REFERENCES entities (
            entity_id
        ),

    CONSTRAINT fk_evidence_parcel_a
        FOREIGN KEY (
            parcel_number_a
        )
        REFERENCES parcels (
            parcel_number
        ),

    CONSTRAINT fk_evidence_parcel_b
        FOREIGN KEY (
            parcel_number_b
        )
        REFERENCES parcels (
            parcel_number
        ),

    /*
        Every Stage 5 pair must have a corresponding
        Stage 6 association.
    */
    CONSTRAINT fk_evidence_association_pair
        FOREIGN KEY (
            entity_id_a,
            entity_id_b
        )
        REFERENCES entity_associations (
            entity_id_a,
            entity_id_b
        ),

    INDEX idx_evidence_pair (
        entity_id_a,
        entity_id_b
    ),

    INDEX idx_evidence_parcel_a (
        parcel_number_a
    ),

    INDEX idx_evidence_parcel_b (
        parcel_number_b
    ),

    INDEX idx_evidence_rule (
        evidence_rule
    ),

    CHECK (
        entity_id_a < entity_id_b
    ),

    CHECK (
        evidence_strength IN (
            'High',
            'Medium',
            'Low'
        )
    ),

    CHECK (
        address_type IS NULL
        OR
        address_type IN (
            'Owner',
            'Taxpayer'
        )
    )
);

-- ==========================================================
-- 6. ENTITY OCCURRENCES
-- Stage 1 lineage / audit table
-- ==========================================================

CREATE TABLE entity_occurrences (
    occurrence_id BIGINT UNSIGNED NOT NULL,

    parcel_number VARCHAR(32) NOT NULL,

    entity_id BIGINT UNSIGNED NOT NULL,

    entity_name VARCHAR(255) NOT NULL,

    associated_address VARCHAR(255) NULL,

    role VARCHAR(32) NOT NULL,

    source_entity_name VARCHAR(255) NOT NULL,

    source_column VARCHAR(64) NOT NULL,

    source_occurrence_id BIGINT UNSIGNED NOT NULL,

    owner_line_continuation_applied BOOLEAN NOT NULL,

    owner_line_continuation_rule VARCHAR(96) NULL,

    entity_type VARCHAR(32) NOT NULL,

    joint_parse_rule VARCHAR(96) NULL,

    joint_parse_confidence VARCHAR(16) NULL,

    joint_expanded BOOLEAN NOT NULL,

    joint_party_index SMALLINT UNSIGNED NULL,

    joint_party_count SMALLINT UNSIGNED NULL,

    organization_type VARCHAR(64) NULL,

    organization_classification_confidence VARCHAR(16) NULL,

    address_source VARCHAR(64) NULL,

    PRIMARY KEY (
        occurrence_id
    ),

    CONSTRAINT fk_occurrence_parcel
        FOREIGN KEY (
            parcel_number
        )
        REFERENCES parcels (
            parcel_number
        ),

    CONSTRAINT fk_occurrence_entity
        FOREIGN KEY (
            entity_id
        )
        REFERENCES entities (
            entity_id
        ),

    INDEX idx_occurrence_entity (
        entity_id
    ),

    INDEX idx_occurrence_parcel (
        parcel_number
    ),

    INDEX idx_occurrence_source_occurrence (
        source_occurrence_id
    ),

    INDEX idx_occurrence_source_column (
        source_column
    ),

    CHECK (
        entity_type IN (
            'Person',
            'Organization',
            'Joint',
            'Unknown'
        )
    ),

    CHECK (
        joint_parse_confidence IS NULL
        OR
        joint_parse_confidence IN (
            'High',
            'Medium',
            'Low'
        )
    ),

    CHECK (
        organization_classification_confidence IS NULL
        OR
        organization_classification_confidence IN (
            'High',
            'Medium',
            'Low'
        )
    )
);

-- ==========================================================
-- ENTITY ASSOCIATION NEIGHBORS
--
-- Converts normalized A/B pairs into a directional lookup
-- representation for convenient API querying.
-- ==========================================================

CREATE VIEW entity_association_neighbors AS

SELECT
    association_id,

    entity_id_a AS entity_id,
    entity_id_b AS associated_entity_id,

    association_confidence,
    evidence_count,
    evidence_rule_count

FROM entity_associations

UNION ALL

SELECT
    association_id,

    entity_id_b AS entity_id,
    entity_id_a AS associated_entity_id,

    association_confidence,
    evidence_count,
    evidence_rule_count

FROM entity_associations;