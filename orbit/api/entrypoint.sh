#!/bin/bash
set -euo pipefail

export PGPASSWORD="${PGPASSWORD:-}"

echo "Waiting for Postgres at ${PGHOST:-postgres}:${PGPORT:-5432}..."
until pg_isready -h "${PGHOST:-postgres}" -p "${PGPORT:-5432}" -U "${PGUSER:-orbit}" -d "${PGDATABASE:-orbit}" -q; do
  sleep 1
done

echo "Applying migrations..."
psql -h "${PGHOST:-postgres}" -p "${PGPORT:-5432}" -U "${PGUSER:-orbit}" -d "${PGDATABASE:-orbit}" \
  -v ON_ERROR_STOP=1 -f /app/migrations/001_initial.sql

echo "Starting uvicorn..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
