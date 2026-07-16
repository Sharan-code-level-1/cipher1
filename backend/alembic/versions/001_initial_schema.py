"""initial schema — full DDL

Revision ID: 001
Revises:
Create Date: 2026-07-16

Creates the complete AutoClaim AI schema. This is the authoritative production
migration. The same DDL is also available as db/init/001_schema.sql for the
Docker postgres auto-init path.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_SQL = r"""
-- =====================================================================
-- AutoClaim AI — PostgreSQL schema (DDL)
-- Auto-loaded by the postgres container on first init.
-- Mirrors the SQLAlchemy models in backend/app/models.
-- =====================================================================

SET client_min_messages = WARNING;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- fast ILIKE search

-- ---------------------------------------------------------------------
-- USERS & IDENTITY
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                 VARCHAR(320) NOT NULL UNIQUE,
    password_hash         VARCHAR(255) NOT NULL,
    full_name             VARCHAR(200) NOT NULL,
    phone                 VARCHAR(32),
    role                  VARCHAR(40)  NOT NULL DEFAULT 'customer',
    is_active             BOOLEAN      NOT NULL DEFAULT TRUE,
    is_verified           BOOLEAN      NOT NULL DEFAULT FALSE,
    mfa_enabled           BOOLEAN      NOT NULL DEFAULT FALSE,
    mfa_secret            VARCHAR(64),
    failed_login_attempts INTEGER      NOT NULL DEFAULT 0,
    locked_until          TIMESTAMPTZ,
    last_login_at         TIMESTAMPTZ,
    preferences           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT chk_user_role CHECK (role IN
        ('customer','surveyor','insurance_officer','repair_workshop',
         'fraud_analyst','admin','super_admin'))
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_role  ON users (role);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti_hash     VARCHAR(64) NOT NULL UNIQUE,
    family_id    VARCHAR(36) NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked      BOOLEAN     NOT NULL DEFAULT FALSE,
    replaced_by  VARCHAR(36),
    user_agent   VARCHAR(512),
    ip_address   VARCHAR(64),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_refresh_user   ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS ix_refresh_family ON refresh_tokens (family_id);

CREATE TABLE IF NOT EXISTS email_verifications (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_emailverif_user ON email_verifications (user_id);

CREATE TABLE IF NOT EXISTS password_resets (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pwreset_user ON password_resets (user_id);

-- ---------------------------------------------------------------------
-- VEHICLES & POLICIES
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicles (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vin                  VARCHAR(17) NOT NULL,
    registration_number  VARCHAR(32) NOT NULL,
    make                 VARCHAR(80) NOT NULL,
    model                VARCHAR(80) NOT NULL,
    year                 INTEGER     NOT NULL,
    color                VARCHAR(40),
    body_type            VARCHAR(40),
    odometer_km          INTEGER,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_vehicles_owner ON vehicles (owner_id);
CREATE INDEX IF NOT EXISTS ix_vehicles_vin   ON vehicles (vin);
CREATE INDEX IF NOT EXISTS ix_vehicles_reg   ON vehicles (registration_number);
CREATE INDEX IF NOT EXISTS ix_vehicles_make_trgm ON vehicles USING gin (make gin_trgm_ops);

CREATE TABLE IF NOT EXISTS policies (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id    UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    policy_number VARCHAR(64) NOT NULL UNIQUE,
    insurer_name  VARCHAR(120) NOT NULL,
    coverage_type VARCHAR(40)  NOT NULL,
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    sum_insured   NUMERIC(14,2) NOT NULL,
    deductible    NUMERIC(12,2) NOT NULL DEFAULT 0,
    status        VARCHAR(20)   NOT NULL DEFAULT 'active',
    warranty_notes TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_policy_coverage CHECK (coverage_type IN
        ('comprehensive','third_party','zero_dep')),
    CONSTRAINT chk_policy_dates CHECK (end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS ix_policies_vehicle ON policies (vehicle_id);

-- ---------------------------------------------------------------------
-- CLAIMS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_number         VARCHAR(32) NOT NULL UNIQUE,
    customer_id          UUID NOT NULL REFERENCES users(id),
    vehicle_id           UUID NOT NULL REFERENCES vehicles(id),
    policy_id            UUID REFERENCES policies(id),
    assigned_surveyor_id UUID REFERENCES users(id),
    status               VARCHAR(40) NOT NULL DEFAULT 'draft',
    incident_date        TIMESTAMPTZ,
    incident_location    VARCHAR(255),
    incident_lat         DOUBLE PRECISION,
    incident_lng         DOUBLE PRECISION,
    description          TEXT,
    severity             VARCHAR(20),
    fraud_score          NUMERIC(5,2),
    estimated_cost       NUMERIC(14,2),
    approved_amount      NUMERIC(14,2),
    surveyor_notes       TEXT,
    rejection_reason     TEXT,
    warranty_valid       BOOLEAN,
    metadata_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
    submitted_at         TIMESTAMPTZ,
    closed_at            TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_claim_status CHECK (status IN
        ('draft','submitted','ai_processing','fraud_review','surveyor_review',
         'approved','rejected','payment_pending','paid','closed')),
    CONSTRAINT chk_claim_severity CHECK (severity IS NULL OR severity IN
        ('minor','moderate','major','critical','total_loss'))
);
CREATE INDEX IF NOT EXISTS ix_claims_customer ON claims (customer_id);
CREATE INDEX IF NOT EXISTS ix_claims_vehicle  ON claims (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_claims_status   ON claims (status);
CREATE INDEX IF NOT EXISTS ix_claims_number   ON claims (claim_number);

CREATE TABLE IF NOT EXISTS claim_images (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id          UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    storage_key       VARCHAR(512) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type      VARCHAR(100) NOT NULL,
    size_bytes        INTEGER NOT NULL,
    sha256            VARCHAR(64) NOT NULL,
    phash             VARCHAR(32),
    thumbnail_key     VARCHAR(512),
    width             INTEGER,
    height            INTEGER,
    exif_json         JSONB NOT NULL DEFAULT '{}'::jsonb,
    angle_label       VARCHAR(40),
    virus_scan_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_climg_claim  ON claim_images (claim_id);
CREATE INDEX IF NOT EXISTS ix_climg_sha    ON claim_images (sha256);
CREATE INDEX IF NOT EXISTS ix_climg_phash  ON claim_images (phash);

CREATE TABLE IF NOT EXISTS claim_status_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id    UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    from_status VARCHAR(40),
    to_status   VARCHAR(40) NOT NULL,
    actor_id    UUID REFERENCES users(id),
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_csh_claim ON claim_status_history (claim_id);

CREATE TABLE IF NOT EXISTS damage_detections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    image_id        UUID REFERENCES claim_images(id) ON DELETE SET NULL,
    model_version   VARCHAR(40) NOT NULL DEFAULT 'yolov11-cv-1.0',
    parts           JSONB NOT NULL DEFAULT '[]'::jsonb,
    damages         JSONB NOT NULL DEFAULT '[]'::jsonb,
    severity        VARCHAR(20) NOT NULL,
    damage_area_pct NUMERIC(6,2) NOT NULL DEFAULT 0,
    confidence      NUMERIC(5,4) NOT NULL DEFAULT 0,
    explanation     JSONB NOT NULL DEFAULT '{}'::jsonb,
    heatmap_key     VARCHAR(512),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_det_claim ON damage_detections (claim_id);

CREATE TABLE IF NOT EXISTS cost_estimates (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id       UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    currency       VARCHAR(3) NOT NULL DEFAULT 'INR',
    parts_total    NUMERIC(14,2) NOT NULL DEFAULT 0,
    labour_total   NUMERIC(14,2) NOT NULL DEFAULT 0,
    painting_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    taxes_total    NUMERIC(14,2) NOT NULL DEFAULT 0,
    grand_total    NUMERIC(14,2) NOT NULL DEFAULT 0,
    repair_days    INTEGER NOT NULL DEFAULT 1,
    line_items     JSONB NOT NULL DEFAULT '[]'::jsonb,
    invoice_json   JSONB NOT NULL DEFAULT '{}'::jsonb,
    explanation    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_cost_claim ON cost_estimates (claim_id);

-- ---------------------------------------------------------------------
-- FRAUD
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fraud_assessments (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id       UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    risk_score     NUMERIC(5,2) NOT NULL,
    risk_level     VARCHAR(20)  NOT NULL,
    summary        TEXT NOT NULL,
    explanation    JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version  VARCHAR(40) NOT NULL DEFAULT 'fraud-engine-1.0',
    reviewed_by    UUID REFERENCES users(id),
    review_decision VARCHAR(40),
    review_notes   TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_fraud_level CHECK (risk_level IN ('low','medium','high','critical'))
);
CREATE INDEX IF NOT EXISTS ix_fraud_claim ON fraud_assessments (claim_id);

CREATE TABLE IF NOT EXISTS fraud_signals (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES fraud_assessments(id) ON DELETE CASCADE,
    signal_type   VARCHAR(60) NOT NULL,
    severity      VARCHAR(20) NOT NULL,
    weight        NUMERIC(5,2) NOT NULL DEFAULT 0,
    message       TEXT NOT NULL,
    evidence      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_fsig_assessment ON fraud_signals (assessment_id);
CREATE INDEX IF NOT EXISTS ix_fsig_type       ON fraud_signals (signal_type);

-- ---------------------------------------------------------------------
-- AUDIT / NOTIFICATIONS / SYSTEM
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id      UUID,
    actor_email   VARCHAR(320),
    action        VARCHAR(80) NOT NULL,
    resource_type VARCHAR(60) NOT NULL,
    resource_id   VARCHAR(64),
    ip_address    VARCHAR(64),
    user_agent    VARCHAR(512),
    status        VARCHAR(20) NOT NULL DEFAULT 'success',
    message       TEXT,
    before_state  JSONB,
    after_state   JSONB,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_actor    ON audit_logs (actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_action   ON audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_resource ON audit_logs (resource_type, resource_id);
CREATE INDEX IF NOT EXISTS ix_audit_created  ON audit_logs (created_at DESC);

CREATE TABLE IF NOT EXISTS notifications (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel       VARCHAR(20) NOT NULL DEFAULT 'in_app',
    title         VARCHAR(200) NOT NULL,
    body          TEXT NOT NULL,
    is_read       BOOLEAN NOT NULL DEFAULT FALSE,
    link          VARCHAR(512),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_notif_user ON notifications (user_id);

CREATE TABLE IF NOT EXISTS feature_flags (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         VARCHAR(80) NOT NULL UNIQUE,
    enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    config      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS system_settings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         VARCHAR(80) NOT NULL UNIQUE,
    value       JSONB NOT NULL DEFAULT '{}'::jsonb,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- updated_at auto-touch trigger
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t text;
BEGIN
    FOR t IN
        SELECT unnest(ARRAY[
            'users','refresh_tokens','email_verifications','password_resets',
            'vehicles','policies','claims','claim_images','claim_status_history',
            'damage_detections','cost_estimates','fraud_assessments','fraud_signals',
            'audit_logs','notifications','feature_flags','system_settings'])
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_touch_%1$s ON %1$s;
             CREATE TRIGGER trg_touch_%1$s BEFORE UPDATE ON %1$s
             FOR EACH ROW EXECUTE FUNCTION touch_updated_at();', t);
    END LOOP;
END $$;
"""

DROP_SQL = r"""
DROP TABLE IF EXISTS fraud_signals CASCADE;
DROP TABLE IF EXISTS fraud_assessments CASCADE;
DROP TABLE IF EXISTS cost_estimates CASCADE;
DROP TABLE IF EXISTS damage_detections CASCADE;
DROP TABLE IF EXISTS claim_status_history CASCADE;
DROP TABLE IF EXISTS claim_images CASCADE;
DROP TABLE IF EXISTS claims CASCADE;
DROP TABLE IF EXISTS policies CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS password_resets CASCADE;
DROP TABLE IF EXISTS email_verifications CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS system_settings CASCADE;
DROP TABLE IF EXISTS feature_flags CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP FUNCTION IF EXISTS touch_updated_at() CASCADE;
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite/others: tables are created from SQLAlchemy metadata at app start.
        return
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(DROP_SQL)
