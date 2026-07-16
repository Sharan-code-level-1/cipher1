# AutoClaim AI

**Enterprise Vehicle Damage Assessment & Fraud Detection Platform**

Production-grade insurance claim management ecosystem for the System Siege competition.

## Features

- Vehicle damage detection (YOLOv11-ready pipeline)
- Damage localization & part segmentation
- Severity classification (Minor → Total Loss)
- Repair cost estimation with OEM parts, labour, painting, taxes
- Multi-signal fraud detection with explainable risk scores
- Full claim workflow: upload → AI → fraud → cost → surveyor → approval → payment
- RBAC + ABAC, JWT rotation, audit trail
- Role panels: Customer, Surveyor, Insurance Officer, Workshop, Fraud Analyst, Admin, Super Admin
- Docker / Compose / NGINX / CI-CD ready

## Quick Start

```bash
# Prerequisites: Docker 24+, Docker Compose v2
cp .env.example .env
# Edit secrets in .env before production use

docker compose up --build -d
```

| Service   | URL |
|-----------|-----|
| Frontend  | http://localhost:5173 |
| API       | http://localhost:8000 |
| API Docs  | http://localhost:8000/docs |
| NGINX     | http://localhost:80 |
| Flower    | http://localhost:5555 |

### Default seed users (dev only)

| Email | Password | Role |
|-------|----------|------|
| admin@autoclaim.ai | Admin@12345! | super_admin |
| surveyor@autoclaim.ai | Surveyor@12345! | surveyor |
| customer@autoclaim.ai | Customer@12345! | customer |

## Database

PostgreSQL-first. Schema and seed data are real SQL files:

- `db/init/001_schema.sql` — full DDL (tables, indexes, constraints, triggers)
- `db/init/002_seed.sql` — seed users (real Argon2id hashes), vehicles, policies, sample claims
- Mirrored as Alembic migrations in `backend/alembic/versions/`

On first `docker compose up`, Postgres auto-loads the SQL; the backend also runs
`alembic upgrade head`. See [db/README.md](db/README.md).

Reset DB: `docker compose down -v && docker compose up --build`

## Frontend

The React 19 SPA includes an upgraded Apple-inspired auth/layout system, mobile
navigation, safer multipart uploads, and claim-image client validation. Backend
routes, payload names, role routing, and claim workflow are unchanged.
See `frontend/FRONTEND_UPGRADE_NOTES.md`.

## AI

Damage detection performs **real OpenCV image analysis** (Canny edges, Laplacian
texture variance, contour localization, HSV color classification) — see
`backend/app/ai/damage_detector.py`. The `detect()` contract is YOLOv11-compatible,
so real model weights can be dropped in without changing the rest of the system.

## Architecture

See [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md).

Microservices (modular monolith deployable as services):

- Authentication · Claim · Damage Detection · Fraud · Cost Estimation
- Notification · Analytics · Admin · Audit · File Storage

## Security

Implements OWASP Top 10 / API Top 10 controls: Argon2id passwords, JWT access+refresh rotation, rate limiting, CSP, secure cookies, IDOR guards, magic-byte upload validation, encryption at rest hooks, full audit logging.

Threat model: [docs/security/THREAT_MODEL.md](docs/security/THREAT_MODEL.md)

## Documentation

| Doc | Path |
|-----|------|
| Deployment | docs/guides/DEPLOYMENT.md |
| Testing | docs/guides/TESTING.md |
| Admin Manual | docs/guides/ADMIN_MANUAL.md |
| User Manual | docs/guides/USER_MANUAL.md |
| Security | docs/security/SECURITY.md |
| OpenAPI | http://localhost:8000/openapi.json |

## License

Proprietary — System Siege competition submission.
