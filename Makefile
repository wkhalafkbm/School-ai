.PHONY: dev stop test test-frontend migrate seed setup import-write-tools

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example — review before running."; fi
	@python3 -m venv .venv
	@.venv/bin/pip install -q -r backend/requirements.txt -r backend/requirements-dev.txt
	@cd frontend && npm install
	@echo "Setup complete. Run 'make dev' to start."

dev:
	@if [ ! -f .env ]; then echo "ERROR: .env not found. Run 'make setup' first."; exit 1; fi
	docker compose up --build

stop:
	docker compose down

test:
	cd backend && ../.venv/bin/pytest -v

test-frontend:
	cd frontend && npm test

migrate:
	cd backend && ../.venv/bin/alembic upgrade head

seed:
	cd backend && ../.venv/bin/python -m app.seed

import-write-tools:
	orchestrate tools import --kind openapi --file orchestrate/tools/write_tools.yaml
