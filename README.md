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

## Journey stage vocabulary

Every workflow item, priority-queue row and journey-health key carries a
`stage`, and there is exactly one spelling per stage — the one the sidebar nav
uses:

| Stage | Page |
| --- | --- |
| `admissions` | Admissions |
| `enrollment` | Enrollment |
| `teaching_readiness` | Teaching Readiness |
| `academic_risk` | Academic Risk |
| `progression` | Progression |
| `career_alumni` | Career & Alumni |

Declared in `backend/app/stages.py` and `frontend/src/lib/stages.ts`, offered to
agents as an `enum` in `orchestrate/tools/write_tools.yaml`, and enforced at the
gateway: `POST /api/workflows` rejects any other value with a 422. Workflow item
statuses work the same way — `completed` is the terminal one; `complete` is not
a status.

`backend/tests/test_stage_vocabulary.py` fails if a fixture, the tool spec, a
query or a frontend writer drifts off the list. After changing it, re-import the
write tools so Orchestrate agents see the new enum:

```bash
make import-write-tools
```

## Virtual environment

All Python dependencies are installed into `.venv/` at the repo root. Nothing is installed into the global interpreter. The venv is created automatically by `make setup`.
