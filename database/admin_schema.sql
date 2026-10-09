-- ==========================================================
-- KALAMAZOO COUNTY TREASURY
-- SNAPSHOT / ADMINISTRATIVE SCHEMA
--
-- Prerequisite:
--     Run create_schema.sql first.
--
-- These tables persist across annual generated-data refreshes.
-- ==========================================================

USE kalamazoo_county_treasury;

-- ==========================================================
-- DATA SNAPSHOTS
-- ==========================================================

CREATE TABLE IF NOT EXISTS data_snapshots (
    snapshot_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    snapshot_code VARCHAR(64) NOT NULL,
    tax_year SMALLINT UNSIGNED NOT NULL,

    source_filename VARCHAR(255) NOT NULL,

    loaded_at DATETIME(6) NOT NULL
        DEFAULT CURRENT_TIMESTAMP(6),

    loaded_by VARCHAR(128) DEFAULT NULL,
    notes VARCHAR(1000) DEFAULT NULL,

    PRIMARY KEY (snapshot_id),

    UNIQUE KEY uq_data_snapshots_code (
        snapshot_code
    ),

    KEY idx_data_snapshots_tax_year (
        tax_year
    ),

    CONSTRAINT data_snapshots_chk_tax_year
        CHECK (
            tax_year BETWEEN 2000 AND 2200
        )
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;


-- ==========================================================
-- ACTIVE SNAPSHOT
-- ==========================================================

CREATE TABLE IF NOT EXISTS active_data_snapshot (
    singleton_id TINYINT UNSIGNED NOT NULL,
    snapshot_id BIGINT UNSIGNED NOT NULL,

    PRIMARY KEY (singleton_id),

    CONSTRAINT fk_active_snapshot
        FOREIGN KEY (snapshot_id)
        REFERENCES data_snapshots (snapshot_id),

    CONSTRAINT active_data_snapshot_chk_singleton
        CHECK (
            singleton_id = 1
        )
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;

-- ==========================================================
-- ASSOCIATION SUPPRESSIONS
-- ==========================================================

CREATE TABLE IF NOT EXISTS association_suppressions (
    suppression_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    snapshot_id BIGINT UNSIGNED NOT NULL,

    association_id BIGINT UNSIGNED NOT NULL,

    entity_id_a BIGINT UNSIGNED NOT NULL,
    entity_id_b BIGINT UNSIGNED NOT NULL,

    entity_name_a VARCHAR(255) NOT NULL,
    entity_name_b VARCHAR(255) NOT NULL,

    reason VARCHAR(1000) NOT NULL,

    created_at DATETIME(6) NOT NULL
        DEFAULT CURRENT_TIMESTAMP(6),

    created_by VARCHAR(128) NOT NULL,

    revoked_at DATETIME(6) DEFAULT NULL,
    revoked_by VARCHAR(128) DEFAULT NULL,
    revocation_reason VARCHAR(1000) DEFAULT NULL,

    active_association_id BIGINT UNSIGNED
        GENERATED ALWAYS AS (
            CASE
                WHEN revoked_at IS NULL
                    THEN association_id
                ELSE NULL
            END
        ) STORED,

    PRIMARY KEY (suppression_id),

    KEY idx_association_suppression_snapshot (
        snapshot_id
    ),

    KEY idx_association_suppression_association (
        association_id
    ),

    UNIQUE KEY uq_active_association_suppression (
        snapshot_id,
        active_association_id
    ),

    CONSTRAINT fk_association_suppression_snapshot
        FOREIGN KEY (snapshot_id)
        REFERENCES data_snapshots (snapshot_id),

    CONSTRAINT association_suppressions_chk_pair
        CHECK (
            entity_id_a < entity_id_b
        ),

    CONSTRAINT association_suppressions_chk_revocation
        CHECK (
            (
                revoked_at IS NULL
                AND revoked_by IS NULL
            )
            OR
            (
                revoked_at IS NOT NULL
                AND revoked_by IS NOT NULL
            )
        )
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;