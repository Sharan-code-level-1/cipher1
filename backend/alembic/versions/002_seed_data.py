"""seed baseline data

Revision ID: 002
Revises: 001
Create Date: 2026-07-16
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_SQL = r"""
-- =====================================================================
-- AutoClaim AI — seed data
-- Loaded after 001_schema.sql on first container init.
-- Passwords (dev only):
--   admin@autoclaim.ai     Admin@12345!
--   surveyor@autoclaim.ai  Surveyor@12345!
--   customer@autoclaim.ai  Customer@12345!
--   fraud@autoclaim.ai     Fraud@12345!xx
--   officer@autoclaim.ai   Officer@12345!
--   workshop@autoclaim.ai  Workshop@1234!
-- =====================================================================

-- Users -------------------------------------------------------------
INSERT INTO users (id,email,password_hash,full_name,role,is_active,is_verified)
VALUES
    ('11111111-1111-1111-1111-111111111111','admin@autoclaim.ai','$argon2id$v=19$m=65536,t=3,p=4$2xsDYAzhfO8d49wbozSGUA$APDW06Z/xQyykQ/WeX0a5TUZOEYgZyROSh/ZRNieGEM','Super Admin','super_admin',TRUE,TRUE),
    ('22222222-2222-2222-2222-222222222222','surveyor@autoclaim.ai','$argon2id$v=19$m=65536,t=3,p=4$BaCU0nqP8V6r1fo/J0SotQ$ULIpQgNYdcZ1oAgknUkCrMjw1KdJRGEUk5WAglG/VCM','Lead Surveyor','surveyor',TRUE,TRUE),
    ('33333333-3333-3333-3333-333333333333','customer@autoclaim.ai','$argon2id$v=19$m=65536,t=3,p=4$pbSWci7FuLdWirF2DuE8xw$P/K2Gvp5V38diOCnXbpApJBkGtSZIxIuUTmXvxJB7xI','Demo Customer','customer',TRUE,TRUE),
    ('44444444-4444-4444-4444-444444444444','fraud@autoclaim.ai','$argon2id$v=19$m=65536,t=3,p=4$8d5b6x0jJESo1XrvHUNIqQ$WnwAc4vWV3nthr7c5bbzWORmwlM07h5YnpSMJh+BlTE','Fraud Analyst','fraud_analyst',TRUE,TRUE),
    ('55555555-5555-5555-5555-555555555555','officer@autoclaim.ai','$argon2id$v=19$m=65536,t=3,p=4$5xwDQAjB2DtnrJVSqvWecw$iUWdmZOvZ5JfEliZXjVlv6Zeow0ONguY9AzVCqJsrwA','Insurance Officer','insurance_officer',TRUE,TRUE),
    ('66666666-6666-6666-6666-666666666666','workshop@autoclaim.ai','$argon2id$v=19$m=65536,t=3,p=4$5/x/r1WKUSrFGGPM2RvjfA$onOzHfzsdcUekXsZMAYJiqtFB9tRhLwSCBD8oe7cySk','Repair Workshop','repair_workshop',TRUE,TRUE)
ON CONFLICT (email) DO NOTHING;

-- Vehicles (owned by demo customer) ---------------------------------
INSERT INTO vehicles (id,owner_id,vin,registration_number,make,model,year,color,body_type,odometer_km)
VALUES
    ('aaaaaaaa-0000-0000-0000-000000000001','33333333-3333-3333-3333-333333333333','JTDBR32E720123456','KA01AB1234','Toyota','Innova',2020,'White','SUV',48200),
    ('aaaaaaaa-0000-0000-0000-000000000002','33333333-3333-3333-3333-333333333333','MA3EWDE1S00234567','KA05CD5678','Maruti','Swift',2019,'Red','Hatchback',63100)
ON CONFLICT DO NOTHING;

-- Policies ----------------------------------------------------------
INSERT INTO policies (id,vehicle_id,policy_number,insurer_name,coverage_type,start_date,end_date,sum_insured,deductible,status,warranty_notes)
VALUES
    ('bbbbbbbb-0000-0000-0000-000000000001','aaaaaaaa-0000-0000-0000-000000000001','POL-INNOVA-2024-001','AutoSecure General','comprehensive','2024-01-01','2026-12-31',1200000,5000,'active','Manufacturer warranty valid until 2026.'),
    ('bbbbbbbb-0000-0000-0000-000000000002','aaaaaaaa-0000-0000-0000-000000000002','POL-SWIFT-2024-002','AutoSecure General','comprehensive','2024-03-01','2026-02-28',600000,3000,'active',NULL)
ON CONFLICT (policy_number) DO NOTHING;

-- Sample claims (one approved history, one in surveyor review) -------
INSERT INTO claims (id,claim_number,customer_id,vehicle_id,policy_id,assigned_surveyor_id,status,
    incident_date,incident_location,incident_lat,incident_lng,description,severity,fraud_score,
    estimated_cost,approved_amount,submitted_at)
VALUES
    ('cccccccc-0000-0000-0000-000000000001','CLM-20260710-A1B2C3','33333333-3333-3333-3333-333333333333','aaaaaaaa-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000001','22222222-2222-2222-2222-222222222222','paid',
     '2026-07-08 10:30:00+05:30','MG Road, Bengaluru',12.9756,77.6050,
     'Front bumper and headlight damage from a low-speed collision.','moderate',12.00,
     48500.00,45000.00,'2026-07-08 12:00:00+05:30'),
    ('cccccccc-0000-0000-0000-000000000002','CLM-20260714-D4E5F6','33333333-3333-3333-3333-333333333333','aaaaaaaa-0000-0000-0000-000000000002','bbbbbbbb-0000-0000-0000-000000000002','22222222-2222-2222-2222-222222222222','surveyor_review',
     '2026-07-13 18:15:00+05:30','Outer Ring Road, Bengaluru',12.9260,77.6762,
     'Rear door dent and scratch after parking incident.','minor',8.00,
     14200.00,NULL,'2026-07-13 19:00:00+05:30')
ON CONFLICT (claim_number) DO NOTHING;

-- Status history for the paid claim ---------------------------------
INSERT INTO claim_status_history (claim_id,from_status,to_status,actor_id,note)
VALUES
    ('cccccccc-0000-0000-0000-000000000001',NULL,'draft','33333333-3333-3333-3333-333333333333','Claim created'),
    ('cccccccc-0000-0000-0000-000000000001','draft','submitted','33333333-3333-3333-3333-333333333333','Submitted'),
    ('cccccccc-0000-0000-0000-000000000001','submitted','ai_processing','33333333-3333-3333-3333-333333333333','AI pipeline started'),
    ('cccccccc-0000-0000-0000-000000000001','ai_processing','surveyor_review','22222222-2222-2222-2222-222222222222','Low fraud risk'),
    ('cccccccc-0000-0000-0000-000000000001','surveyor_review','approved','22222222-2222-2222-2222-222222222222','Approved after inspection'),
    ('cccccccc-0000-0000-0000-000000000001','approved','payment_pending','55555555-5555-5555-5555-555555555555','Payment queued'),
    ('cccccccc-0000-0000-0000-000000000001','payment_pending','paid','55555555-5555-5555-5555-555555555555','Settled'),
    ('cccccccc-0000-0000-0000-000000000002',NULL,'draft','33333333-3333-3333-3333-333333333333','Claim created'),
    ('cccccccc-0000-0000-0000-000000000002','draft','submitted','33333333-3333-3333-3333-333333333333','Submitted'),
    ('cccccccc-0000-0000-0000-000000000002','submitted','ai_processing','33333333-3333-3333-3333-333333333333','AI pipeline started'),
    ('cccccccc-0000-0000-0000-000000000002','ai_processing','surveyor_review','22222222-2222-2222-2222-222222222222','Awaiting surveyor')
ON CONFLICT DO NOTHING;

-- Cost estimate for the paid claim ----------------------------------
INSERT INTO cost_estimates (claim_id,currency,parts_total,labour_total,painting_total,taxes_total,grand_total,repair_days,line_items,invoice_json,explanation)
VALUES
    ('cccccccc-0000-0000-0000-000000000001','INR',22000.00,9350.00,4500.00,6448.50,42298.50,3,
     '[{"description":"Replace bumper - dent","category":"parts","oem":true,"amount":12000},{"description":"Replace headlights - broken_light","category":"parts","oem":true,"amount":8000},{"description":"Labour - bumper","category":"labour","amount":2550},{"description":"Painting - bumper","category":"painting","amount":4500}]'::jsonb,
     '{"currency":"INR","subtotal":35850,"tax_rate":0.18,"tax":6453,"grand_total":42303}'::jsonb,
     '{"method":"OEM parts book + labour rate + GST","labour_rate_inr":850,"tax_rate":0.18}'::jsonb)
ON CONFLICT DO NOTHING;

-- Fraud assessment for the paid claim -------------------------------
INSERT INTO fraud_assessments (id,claim_id,risk_score,risk_level,summary,explanation,model_version)
VALUES
    ('dddddddd-0000-0000-0000-000000000001','cccccccc-0000-0000-0000-000000000001',12.00,'low',
     'No fraud signals detected. Risk is low.',
     '{"risk_score":12,"risk_level":"low","signal_count":1,"methodology":"Weighted multi-signal ensemble"}'::jsonb,
     'fraud-engine-1.0')
ON CONFLICT DO NOTHING;

INSERT INTO fraud_signals (assessment_id,signal_type,severity,weight,message,evidence)
VALUES
    ('dddddddd-0000-0000-0000-000000000001','multi_angle_verification','low',12,
     'Only front-angle images supplied; recommend additional angles.','{"count":1}'::jsonb)
ON CONFLICT DO NOTHING;

-- Feature flags & settings ------------------------------------------
INSERT INTO feature_flags (key,enabled,description)
VALUES
    ('enable_virus_scan',FALSE,'Route uploads through virus scanner'),
    ('enable_ai_heatmaps',TRUE,'Generate damage heatmaps'),
    ('maintenance_mode',FALSE,'Global maintenance mode')
ON CONFLICT (key) DO NOTHING;

INSERT INTO system_settings (key,value,description)
VALUES
    ('labour_rate_inr','{"value":850}'::jsonb,'Workshop labour rate per hour'),
    ('gst_rate','{"value":0.18}'::jsonb,'Tax rate applied to estimates'),
    ('fraud_thresholds','{"medium":20,"high":45,"critical":70}'::jsonb,'Fraud risk cutoffs')
ON CONFLICT (key) DO NOTHING;

-- Welcome notification ----------------------------------------------
INSERT INTO notifications (user_id,channel,title,body,link)
VALUES
    ('33333333-3333-3333-3333-333333333333','in_app','Welcome to AutoClaim AI',
     'Your account is ready. Add a vehicle and file your first claim.','/app/claims/new')
ON CONFLICT DO NOTHING;
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(SEED_SQL)


def downgrade() -> None:
    # Seed rows use ON CONFLICT DO NOTHING; leave data intact on downgrade.
    pass
