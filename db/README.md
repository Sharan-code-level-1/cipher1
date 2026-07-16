# Database Layer

AutoClaim AI is **PostgreSQL-first**. There are three consistent ways the schema
gets created; pick based on environment.

## Files

| File | Purpose |
|------|---------|
| `db/init/001_schema.sql` | Full DDL: tables, indexes, constraints, trigrams, `updated_at` triggers |
| `db/init/002_seed.sql`   | Seed users (real Argon2id hashes), vehicles, policies, sample claims, settings |
| `backend/alembic/versions/001_initial_schema.py` | Alembic migration wrapping the same DDL |
| `backend/alembic/versions/002_seed_data.py` | Alembic migration wrapping the seed |

The DDL in the migration and in `db/init` are kept identical.

## How schema is applied

### 1. Docker Compose (default)
`docker-compose.yml` mounts `./db/init` into the Postgres container's
`/docker-entrypoint-initdb.d`. On the **first** boot of an empty data volume,
Postgres runs `001_schema.sql` then `002_seed.sql` automatically.

The backend container additionally runs `alembic upgrade head` on start
(idempotent — safe if the SQL already created everything).

### 2. Production (migrations)
```bash
cd backend
alembic upgrade head      # applies schema + seed
```
Use a managed Postgres and run this as a release/job step.

### 3. Dev / tests (SQLite or Postgres)
When `APP_ENV != production`, the app auto-creates tables from SQLAlchemy
metadata at startup and seeds demo users. Tests use an in-memory SQLite DB via
portable column types (`GUID`, `JSONVariant` in `app/db/base.py`).

## Seed accounts (dev only — rotate before production)

| Email | Password | Role |
|-------|----------|------|
| admin@autoclaim.ai | Admin@12345! | super_admin |
| surveyor@autoclaim.ai | Surveyor@12345! | surveyor |
| customer@autoclaim.ai | Customer@12345! | customer |
| fraud@autoclaim.ai | Fraud@12345!xx | fraud_analyst |
| officer@autoclaim.ai | Officer@12345! | insurance_officer |
| workshop@autoclaim.ai | Workshop@1234! | repair_workshop |

## Reset the database (Docker)

```bash
docker compose down -v      # drops the pgdata volume
docker compose up --build   # re-runs init SQL on fresh volume
```

## Regenerating password hashes

```bash
cd backend
python -c "from passlib.context import CryptContext; \
print(CryptContext(schemes=['argon2']).hash('YourPassword!'))"
```
