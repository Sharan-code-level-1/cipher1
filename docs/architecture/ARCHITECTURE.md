# AutoClaim AI — System Architecture

## Overview

AutoClaim AI is an enterprise vehicle damage assessment and fraud detection platform. It is implemented as a **modular monolith** that can be split along service boundaries into independently scalable workers/services.

```
                   ┌────────────┐
                   │   NGINX    │  TLS termination, rate limits, reverse proxy
                   └─────┬──────┘
           ┌─────────────┴─────────────┐
           ▼                           ▼
    ┌─────────────┐             ┌─────────────┐
    │  React SPA  │             │   FastAPI   │
    │  (Vite)     │             │   API GW    │
    └─────────────┘             └──────┬──────┘
                                       │
              ┌───────────────┬────────┼────────┬──────────────┐
              ▼               ▼        ▼        ▼              ▼
        PostgreSQL         Redis    Celery   File Store    Mailhog
        (claims,           (cache,  workers  (images,      (dev email)
         users,            sessions, AI jobs  thumbs)
         audit)            broker)
```

## Microservices (logical modules)

| Service | Responsibility |
|---------|----------------|
| Authentication | Register/login, JWT rotation, lockout, password reset |
| Claim | Claim lifecycle, status machine, IDOR-safe access |
| Damage Detection | YOLOv11-compatible inference interface |
| Fraud Detection | Multi-signal risk scoring + explanations |
| Cost Estimation | OEM parts, labour, paint, tax invoice |
| Notification | Email/SMS/in-app |
| Analytics | Dashboard aggregations |
| Admin | Users, RBAC, feature flags, settings |
| Audit | Immutable security/event trail |
| File Storage | Magic-byte validation, thumbs, signed path access |

## Claim workflow

```
Customer → Upload Images → AI Detection → Fraud Detection
→ Cost Estimation → Surveyor Review → Approval → Payment → History
```

## Data stores

- **PostgreSQL**: transactional system of record
- **Redis**: rate limiting support, Celery broker/backend
- **Filesystem / object storage path**: claim images (AES-at-rest helpers available)

## Frontend architecture

- React 19 + TypeScript + Vite
- React Query for server state
- Zustand for auth/theme
- Role-based route shells: Customer, Surveyor, Admin
- Chart.js dashboards, dark/light + reduced-motion support

## Security architecture

Defense in depth: edge rate limits (NGINX) → app rate limits (SlowAPI) → JWT access/refresh rotation with reuse detection → RBAC permission checks → ORM parameterized queries → upload magic-byte validation → security headers (CSP, HSTS, frame deny) → structured audit logs.

See `docs/security/SECURITY.md` and `docs/security/THREAT_MODEL.md`.
