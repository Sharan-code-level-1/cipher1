# Testing Guide

## Backend unit tests

```bash
cd backend
pip install -r requirements.txt aiosqlite
export SECRET_KEY=test-secret-key-min-32-characters-long!!
export DATABASE_URL=sqlite+aiosqlite:///:memory:
export DATABASE_URL_SYNC=sqlite:///:memory:
export FILE_STORAGE_PATH=/tmp/autoclaim-test
export APP_ENV=test
pytest -q
```

Coverage areas:
- Password hashing / JWT / encryption
- RBAC matrix
- Damage detector + cost estimator
- Upload validation / path traversal
- OWASP-oriented security checks

## Integration

Use Docker Compose and exercise:
1. Register/login
2. Create vehicle
3. Create claim + upload image + submit
4. Surveyor approve
5. Admin dashboard + audit logs

## Security testing

- Attempt IDOR on `/api/v1/claims/{id}` with another user
- Upload non-image polyglot
- Reuse rotated refresh token (expect family revoke)
- Brute force login (expect lockout)
