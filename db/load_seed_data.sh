#!/bin/bash
set -e

echo "Checking schema.sql exists..."
if [ ! -f "db/schema.sql" ]; then
    echo "Error: schema.sql not found!"
    exit 1
fi

echo "Creating database schema..."
docker compose exec -T db psql -U hrm_user -d hrm_db -f /docker-entrypoint-initdb.d/01-schema.sql

echo "Verifying table creation..."
docker compose exec -T db psql -U hrm_user -d hrm_db -c "\d employees"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create employees table!"
    echo "Checking database logs..."
    docker compose logs db
    exit 1
fi

echo "Loading seed data..."
docker compose exec -T db psql -U hrm_user -d hrm_db -f /docker-entrypoint-initdb.d/02-seed_data.sql

echo "Verifying data load..."
docker compose exec -T db psql -U hrm_user -d hrm_db -c "SELECT COUNT(*) FROM employees;"
