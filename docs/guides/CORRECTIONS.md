# Corrections applied (full monorepo audit)

## Frontend
- Your uploaded frontend is used **byte-for-byte** (source only; no node_modules/dist).
- Verified with MD5: every source file matches the upload.
- No frontend logic was rewritten.

## Backend / API fixes required for that frontend
1. **Logout** — frontend calls `POST /auth/logout` with no body.
   - Fixed to accept empty body and revoke all refresh tokens for the user.
2. **Health checks** — Docker/NGINX expected `/health` and `/api/v1/health`.
   - Added root `/health` alias and fixed Docker HEALTHCHECK to use `/api/v1/health`.
3. **Model metadata** — `create_all` only registered User table.
   - Import full `app.models` package so all tables are created.
4. **Vehicle route order** — `POST /vehicles/policies` could be shadowed by `/{vehicle_id}`.
   - Static `/policies` route registered before path params.
5. **NGINX request id** — undefined `$request_id` usage.
   - Added map for `$req_id`.
6. **Compose** — frontend waited on backend without healthy condition; health path wrong.
   - Fixed healthchecks, start_period, frontend depends_on healthy backend.
7. **Frontend Docker build** — uses `npm ci` when lockfile present.

## SQL
- `db/init/001_schema.sql` and `002_seed.sql` remain the production schema/seed.
- Alembic 001/002 wrap the same SQL for migration-based deploys.

## Tests
- Unit + security + integration suite must pass after these fixes.
