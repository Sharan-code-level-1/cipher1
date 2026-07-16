# API Documentation

Interactive OpenAPI: `GET /docs` and `GET /openapi.json`

## Base URL
`/api/v1`

## Auth
`Authorization: Bearer <access_token>`

### Endpoints (selected)

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/register | Create customer |
| POST | /auth/login | Login |
| POST | /auth/refresh | Rotate tokens |
| GET | /auth/me | Current user |
| POST | /vehicles | Add vehicle |
| GET | /vehicles | List vehicles |
| POST | /claims | Create claim |
| POST | /claims/{id}/images | Upload image |
| POST | /claims/{id}/submit | Run AI pipeline |
| GET | /claims/{id} | Claim detail |
| PATCH | /claims/{id}/status | Transition status |
| GET | /admin/dashboard | Analytics |
| GET | /admin/users | List users |
| GET | /admin/audit-logs | Audit trail |
| GET | /search?q= | Global search |
| GET | /health | Health check |
