# University AI Operating Center

**Student Journey Intelligence Layer** — a leadership-facing demo application that surfaces AI-driven insights across the full student lifecycle.

## Quick start

**Prerequisites:** Python 3.12+, Docker, Docker Compose, Node.js 22+

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd School-ai

# 2. Bootstrap venv and copy .env
make setup

# 3. Review .env and adjust UNIVERSITY_NAME if needed

# 4. Start the full stack
make dev
```

The stack starts at:

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:3000      |
| Backend  | http://localhost:8000      |
| API docs | http://localhost:8000/docs |

## Development

```bash
# Run backend tests
make test

# Apply database migrations
make migrate

# Seed the demo database
make seed

# Stop containers
make stop
```

## Environment variables

Copy `.env.example` to `.env` before running. Key variables:

| Variable              | Description                                         | Default                                |
|-----------------------|-----------------------------------------------------|----------------------------------------|
| `UNIVERSITY_NAME`     | University name shown in the app header             | `University AI Operating Center`       |
| `AI_MODE`             | `scripted` / `live` / `hybrid`                      | `scripted`                             |
| `DATABASE_URL`        | PostgreSQL connection string                        | `postgresql://uniai:uniai@localhost…`  |
| `IBM_CLOUD_API_KEY`   | Required for `live` or `hybrid` AI mode             | *(empty)*                              |
| `ORCHESTRATE_INSTANCE_ID` | watsonx Orchestrate instance ID               | *(empty)*                              |

## Project layout

```
School-ai/
├── backend/            # Python / FastAPI
│   ├── app/            # Application code
│   ├── alembic/        # Database migrations
│   ├── tests/          # pytest test suite
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/           # Next.js
│   └── src/app/
├── .env.example
├── docker-compose.yml
└── Makefile
```

## Virtual environment

All Python dependencies are installed into `.venv/` at the repo root. Nothing is installed into the global interpreter. The venv is created automatically by `make setup`.
