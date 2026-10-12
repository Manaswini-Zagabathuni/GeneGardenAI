.PHONY: dev up down migrate ingest-starter benchmark api-test api-lint web-test web-lint web-format web-build check

dev:
	docker compose up --build

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	cd apps/api && alembic upgrade head

ingest-starter:
	cd apps/api && python -m genegarden_api.cli.ingest --manifest resources/starter_domain.json

benchmark:
	cd apps/api && python -m genegarden_api.cli.benchmark --benchmark resources/benchmarks/oncology_open_targets_26_09.json --k 5

api-test:
	cd apps/api && python -m pytest

api-lint:
	cd apps/api && python -m ruff check . && python -m ruff format --check .

web-test:
	npm run test:web

web-lint:
	npm run lint:web

web-format:
	npm run format:web

web-build:
	npm run build:web

check: api-lint api-test benchmark web-lint web-format web-test web-build
