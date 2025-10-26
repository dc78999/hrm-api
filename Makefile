.PHONY: generate-seed-data up down reset-db

generate-seed-data:
	@echo "Generating seed data..."
	python db/generate_seed_data.py

up:
	docker-compose up -d

down:
	docker-compose down

reset-db: down
	docker-compose down -v
	docker-compose up -d
