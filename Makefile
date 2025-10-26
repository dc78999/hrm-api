.PHONY: install-dev generate-seed-data db-up db-down db-reset psql

install-dev:
	pip install -r requirements-dev.txt

generate-seed-data:
	python db/generate_seed_data.py

db-up:
	docker compose up -d db

db-down:
	docker compose down

db-reset: db-down
	docker volume rm hrm-api_postgres_data || true
	docker compose up -d db

psql:
	docker compose exec db psql -U hrm_user -d hrm_db
