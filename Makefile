.PHONY: dev stop test migrate seed setup

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example — review before running."; fi
	@python3 -m venv .venv
	@.venv/bin/pip install -q -r backend/requirements.txt -r backend/requirements-dev.txt
	@echo "Setup complete. Run 'make dev' to start."

dev:
	@if [ ! -f .env ]; then echo "ERROR: .env not found. Run 'make setup' first."; exit 1; fi
	docker compose up --build

stop:
	docker compose down

test:
	cd backend && ../.venv/bin/pytest -v

migrate:
	cd backend && ../.venv/bin/alembic upgrade head

seed:
	cd backend && ../.venv/bin/python -m app.seed
