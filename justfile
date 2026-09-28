# === Code Quality (local, no DB needed) ===

# Format backend code
format:
    cd backend && uv run ruff check app --fix && uv run ruff format app

# Lint backend code (type-check + style)
lint:
    cd backend && uv run python -m ty check app && uv run ruff check app && uv run ruff format app --check

# Strict type check (pyrefly, manual opt-in, not part of `check`)
type-check-strict:
    cd backend && uv run python -m pyrefly check

# === Docker Stack ===

# Start full containerized stack (db, backend, frontend, mailpit, adminer, proxy)
up:
    docker compose up -d --wait db adminer backend mailpit proxy
    docker compose exec -T backend uv run python -m alembic upgrade head
    docker compose exec -T backend uv run python app/initial_data.py

# Stop containerized stack (keeps volumes)
down:
    docker compose down

# Stop stack and remove volumes + orphans
down-clean:
    docker compose down -v --remove-orphans

# === Testing ===

# Run backend tests locally (requires running `docker compose up -d db`)
test-local:
    cd backend && rm -rf htmlcov && FASTAPI_ENV=development uv run pytest

# Run backend tests in containerized stack
test:
    docker compose exec -T backend rm -rf htmlcov
    docker compose exec -T -e FASTAPI_ENV=development backend uv run pytest

# Full CI-like suite: build, run, test, cleanup
test-ci:
    docker compose build
    docker compose down -v --remove-orphans
    docker compose run --rm backend uv run python -m alembic upgrade head
    docker compose up -d
    docker compose exec -T -e FASTAPI_ENV=development backend uv run pytest
    docker compose down -v --remove-orphans

# === Code Generation & Integration ===

# Generate OpenAPI client SDK from running backend
generate-client:
    cd backend && FASTAPI_ENV=development uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../openapi.json && \
    cd .. && mv openapi.json frontend/ && \
    bun run --filter frontend generate-client && \
    bun run lint

# === Quality Gates ===

# All quality checks: lint + test (gates CI)
check:
    just lint
    just test-local

# Fix code: format + frontend lint + generate SDK
fix:
    just format
    bun run lint
    just generate-client
