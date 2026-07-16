# Admin Manual

## Roles
- **Admin**: users (non super), analytics, config, claim oversight
- **Super Admin**: full permission set, backups, feature flags, certificates

## Daily operations
1. Open **Enterprise dashboard** for pending/fraud KPIs
2. Review **Audit logs** for anomalies
3. Manage users under **Users**
4. Inspect high fraud-score claims in surveyor queue

## Seed accounts (dev only)
See root README. Rotate/disable before production.

## Incident response
1. Disable compromised user (`is_active=false`)
2. Revoke refresh tokens (password reset flow revokes all)
3. Export relevant audit rows
4. Enable maintenance mode / feature flags as needed
