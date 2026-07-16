#!/usr/bin/env bash
# Apply database migrations (schema + seed). Postgres only.
set -euo pipefail
cd "$(dirname "$0")/../backend"
echo "Running alembic upgrade head..."
alembic upgrade head
echo "Done."
