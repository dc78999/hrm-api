#!/bin/bash
set -e

echo "Checking database connection..."
docker compose exec -T db pg_isready -U hrm_user -d hrm_db

echo "Checking if schema exists..."
docker compose exec -T db psql -U hrm_user -d hrm_db -c "\dt employees"
if [ $? -ne 0 ]; then
    echo "Creating database schema..."
    docker compose exec -T db psql -U hrm_user -d hrm_db < db/schema.sql
    if [ $? -ne 0 ]; then
        echo "Failed to create schema!"
        exit 1
    fi
fi

