.PHONY: install-dev generate-seed-data db-up db-down db-reset psql load-seed-data init-db

install-dev:
	pip install -r requirements-dev.txt

generate-seed-data:
	python3 db/generate_seed_data.py

db-up:
	docker compose up -d db

db-down:
	docker compose down

db-reset: db-down
	docker volume rm hrm-api_postgres_data || true
	docker compose up -d db

psql:
	docker compose exec db psql -U hrm_user -d hrm_db

load-seed-data:
	@chmod +x db/load_seed_data.sh
	@./db/load_seed_data.sh

init-db: db-down
	@echo "Starting fresh database..."
	@docker compose up -d db
	@echo "Waiting for database to be ready..."
	@sleep 10
	@chmod +x db/load_seed_data.sh
	@chmod +x db/init_db.sh
	@./db/init_db.sh || (echo "Failed to initialize database" && exit 1)
	@./db/load_seed_data.sh || (echo "Failed to initialize database" && exit 1)

verify-db:
	@echo "Verifying database setup..."
	@docker compose exec db psql -U hrm_user -d hrm_db -c "\d employees"

preview-seed:
	@echo "Preview of seed_data.sql:"
	@head -n 20 db/seed_data.sql

preview-db:
	@echo "\nSample employees data:"
	@docker compose exec -T db psql -U hrm_user -d hrm_db -c "\
		SELECT company, first_name, last_name, department, position \
		FROM employees LIMIT 5;"
	@echo "\nCount by company:"
	@docker compose exec -T db psql -U hrm_user -d hrm_db -c "\
		SELECT company, count(*) as employee_count \
		FROM employees GROUP BY company ORDER BY employee_count DESC;"

# Reset everything and reinitialize
full-reset: db-reset init-db
