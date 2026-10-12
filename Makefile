NODE ?= $(shell command -v node 2>/dev/null)

.PHONY: dev up down migrate ingest-starter benchmark api-test api-lint web-test web-lint web-format web-build check local-venv-check local-node-check local-migrate local-ingest-starter dev-api-local dev-web-local

dev:
	docker compose up --build

up:
	docker compose up -d --build

down:
	docker compose down

local-venv-check:
	@test -x work/venv/bin/python || (echo "Missing work/venv. Create it with: python3.12 -m venv work/venv" && exit 1)

local-node-check:
	@test -x "$(NODE)" || (echo "Node.js was not found. Set NODE=/absolute/path/to/node or install Node.js 22.12+." && exit 1)
	@test -f node_modules/vite/bin/vite.js || (echo "Vite is missing. Install frontend dependencies before starting the web app." && exit 1)

local-migrate: local-venv-check
	cd apps/api && ../../work/venv/bin/python -m alembic upgrade head

local-ingest-starter: local-venv-check
	cd apps/api && ../../work/venv/bin/python -m genegarden_api.cli.ingest --manifest resources/starter_domain.json

dev-api-local: local-venv-check
	cd apps/api && ../../work/venv/bin/python -m uvicorn genegarden_api.main:app --host 127.0.0.1 --port 8000 --reload

dev-web-local: local-node-check
	cd apps/web && "$(NODE)" ../../node_modules/vite/bin/vite.js --host 0.0.0.0

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
