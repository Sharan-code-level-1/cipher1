"""AI provider settings, test history, reports, and evidence pipeline tables

Revision ID: 003
Revises: 002
Create Date: 2026-07-16

Adds the schema for the layered AI claim-processing pipeline:
  - ai_provider_settings / ai_provider_test_history (BYOK VLM config)
  - ai_reports (vision-LLM narrative + structured output per claim)
  - evidence_store (per-image layered engine results)
  - consolidated_damages (fused claim-level damage)
  - evidence_risk_assessments / evidence_risk_signals (explainable risk)
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_SQL = r"""
SET client_min_messages = WARNING;

-- ---------------------------------------------------------------------
-- AI PROVIDERS (BYOK VLM)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_provider_settings (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider          VARCHAR(40)  NOT NULL,
    label             VARCHAR(120) NOT NULL,
    model             VARCHAR(120) NOT NULL,
    base_url          VARCHAR(512),
    api_key_encrypted TEXT,
    is_enabled        BOOLEAN      NOT NULL DEFAULT TRUE,
    is_default        BOOLEAN      NOT NULL DEFAULT FALSE,
    config            JSONB        NOT NULL DEFAULT '{}'::jsonb,
    last_tested_at    TIMESTAMPTZ,
    last_test_status  VARCHAR(20),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT chk_ai_provider CHECK (provider IN ('openai','anthropic','google','custom'))
);
CREATE INDEX IF NOT EXISTS ix_aiprov_provider ON ai_provider_settings (provider);
CREATE INDEX IF NOT EXISTS ix_aiprov_default  ON ai_provider_settings (is_default);

CREATE TABLE IF NOT EXISTS ai_provider_test_history (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id      UUID NOT NULL REFERENCES ai_provider_settings(id) ON DELETE CASCADE,
    status           VARCHAR(20) NOT NULL,
    latency_ms       INTEGER,
    message          TEXT,
    request_summary  JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    tested_by        UUID REFERENCES users(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_aitest_provider ON ai_provider_test_history (provider_id);

CREATE TABLE IF NOT EXISTS ai_reports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id          UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    provider_id       UUID REFERENCES ai_provider_settings(id) ON DELETE SET NULL,
    provider_name     VARCHAR(120) NOT NULL DEFAULT 'unconfigured',
    model             VARCHAR(120) NOT NULL DEFAULT 'none',
    status            VARCHAR(20)  NOT NULL DEFAULT 'skipped',
    summary           TEXT,
    report_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
    prompt            TEXT,
    raw_response      TEXT,
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    error_message     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_ai_report_status CHECK (status IN ('generated','skipped','error'))
);
CREATE INDEX IF NOT EXISTS ix_aireport_claim ON ai_reports (claim_id);

-- ---------------------------------------------------------------------
-- EVIDENCE PIPELINE
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence_store (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id            UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    image_id            UUID REFERENCES claim_images(id) ON DELETE SET NULL,
    sha256              VARCHAR(64),
    phash               VARCHAR(32),
    embedding           JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_result   JSONB NOT NULL DEFAULT '{}'::jsonb,
    verification_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    damage_result       JSONB NOT NULL DEFAULT '{}'::jsonb,
    similarity_result   JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_evstore_claim ON evidence_store (claim_id);
CREATE INDEX IF NOT EXISTS ix_evstore_image ON evidence_store (image_id);
CREATE INDEX IF NOT EXISTS ix_evstore_sha   ON evidence_store (sha256);
CREATE INDEX IF NOT EXISTS ix_evstore_phash ON evidence_store (phash);

CREATE TABLE IF NOT EXISTS consolidated_damages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    model_version   VARCHAR(60) NOT NULL DEFAULT 'fusion-1.0',
    fusion_method   VARCHAR(60) NOT NULL DEFAULT 'max_confidence_union',
    parts           JSONB NOT NULL DEFAULT '[]'::jsonb,
    damages         JSONB NOT NULL DEFAULT '[]'::jsonb,
    severity        VARCHAR(20) NOT NULL DEFAULT 'minor',
    damage_area_pct NUMERIC(6,2) NOT NULL DEFAULT 0,
    confidence      NUMERIC(5,4) NOT NULL DEFAULT 0,
    image_count     INTEGER NOT NULL DEFAULT 0,
    explanation     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_consdmg_claim ON consolidated_damages (claim_id);

CREATE TABLE IF NOT EXISTS evidence_risk_assessments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id          UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    risk_score        NUMERIC(5,2) NOT NULL,
    risk_level        VARCHAR(20)  NOT NULL,
    summary           TEXT NOT NULL,
    metadata_findings JSONB NOT NULL DEFAULT '{}'::jsonb,
    rules_fired       JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation       JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version     VARCHAR(40) NOT NULL DEFAULT 'risk-engine-1.0',
    reviewed_by       UUID REFERENCES users(id),
    review_decision   VARCHAR(40),
    review_notes      TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_risk_level CHECK (risk_level IN ('low','medium','high','critical'))
);
CREATE INDEX IF NOT EXISTS ix_riskassess_claim ON evidence_risk_assessments (claim_id);

CREATE TABLE IF NOT EXISTS evidence_risk_signals (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES evidence_risk_assessments(id) ON DELETE CASCADE,
    signal_type   VARCHAR(60) NOT NULL,
    severity      VARCHAR(20) NOT NULL,
    weight        NUMERIC(5,2) NOT NULL DEFAULT 0,
    message       TEXT NOT NULL,
    evidence      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_risksig_assessment ON evidence_risk_signals (assessment_id);
CREATE INDEX IF NOT EXISTS ix_risksig_type       ON evidence_risk_signals (signal_type);

-- Attach updated_at auto-touch trigger to the new tables
DO $$
DECLARE t text;
BEGIN
    FOR t IN
        SELECT unnest(ARRAY[
            'ai_provider_settings','ai_provider_test_history','ai_reports',
            'evidence_store','consolidated_damages',
            'evidence_risk_assessments','evidence_risk_signals'])
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_touch_%1$s ON %1$s;
             CREATE TRIGGER trg_touch_%1$s BEFORE UPDATE ON %1$s
             FOR EACH ROW EXECUTE FUNCTION touch_updated_at();', t);
    END LOOP;
END $$;
"""

DROP_SQL = r"""
DROP TABLE IF EXISTS evidence_risk_signals CASCADE;
DROP TABLE IF EXISTS evidence_risk_assessments CASCADE;
DROP TABLE IF EXISTS consolidated_damages CASCADE;
DROP TABLE IF EXISTS evidence_store CASCADE;
DROP TABLE IF EXISTS ai_reports CASCADE;
DROP TABLE IF EXISTS ai_provider_test_history CASCADE;
DROP TABLE IF EXISTS ai_provider_settings CASCADE;
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
