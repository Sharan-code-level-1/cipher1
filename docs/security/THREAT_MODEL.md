# Threat Model — AutoClaim AI

## Assets
- User credentials and session tokens
- PII (name, email, phone)
- Vehicle VIN / registration
- Claim images and EXIF
- Fraud decisions and audit logs
- Pricing / invoice data

## Actors
- Honest customer
- Fraudulent claimant
- Compromised surveyor account
- External attacker (internet)
- Insider admin

## STRIDE summary

| Threat | Example | Mitigation |
|--------|---------|------------|
| Spoofing | Stolen password | Argon2, lockout, JWT expiry, MFA-ready |
| Tampering | Edited damage photo | Hashing, phash, EXIF/edit signals, audit |
| Repudiation | Deny approval action | Immutable audit logs |
| Info disclosure | IDOR on claims | Owner checks + RBAC |
| DoS | Upload flood | Size limits, rate limits, NGINX |
| Elevation | Customer → admin | Permission matrix, super-admin gates |

## Trust boundaries
1. Browser ↔ NGINX
2. NGINX ↔ API
3. API ↔ PostgreSQL/Redis/Storage
4. Worker ↔ shared DB/storage

## High-risk flows
1. Image upload → AI pipeline
2. Claim approval / payment amount
3. Refresh token rotation
4. Admin user/role management
