# Backend — docsinsights

**Updated:** 2026-09-29

## Requirements

* [Docker](https://www.docker.com/)
* [uv](https://docs.astral.sh/uv/) for Python package and environment management
* [Bun](https://bun.sh/) (for frontend/email templates)

## Quick Start

From the project root:

```console
just up
```

This starts the full stack (PostgreSQL, backend, frontend) with migrations applied. Backend API is at `http://localhost:8000/docs`.

To stop: `just down`

## Local Development (Backend Only)

Run backend tests and development server without the frontend:

```console
docker compose up -d db mailpit
uv sync
just prestart
cd backend && uv run fastapi dev
```

Backend API: `http://localhost:8000/docs`

## Development Workflow

* Run commands from `./backend/` with `uv run`
* Editor: use Python at `.venv/bin/python` (project root)
* Models: `./backend/app/models.py` (SQLModel + database schema)
* Routes: `./backend/app/api/` (FastAPI endpoints by domain)
* CRUD: `./backend/app/crud.py` (database queries by entity)

## VS Code

Debugger and test runner are pre-configured in `.vscode/launch.json`.

## Full Stack with Docker Compose

To run the backend and built frontend in Docker Compose:

```console
docker compose run --rm backend uv run alembic upgrade head
docker compose watch
```

The application is available at `http://localhost:8000`.

### Docker Compose Override

The `compose.override.yml` file contains local settings for published ports, source synchronization, automatic image rebuilds, and backend reloads. Docker Compose applies it automatically when you run `docker compose` without an explicit file list.

To open a shell in the backend container:

```console
docker compose exec backend bash
```

## Backend Tests

To test the backend, run from the project root:

```console
just test
```

The tests run with Pytest. Modify existing tests or add new ones in `./backend/tests/`.

If you use GitHub Actions, the tests will run automatically.

### Test a Running Stack

If your stack is already up and you just want to run the tests, you can use:

```bash
docker compose exec backend uv run pytest tests/ -x
```

Pass extra arguments to `pytest` as needed (e.g., `-x` to stop on first error).

### Test Coverage

When the tests run, they generate `htmlcov/index.html`. Open it in your browser to inspect the test coverage.

## Migrations

Make sure you create a revision of your models and upgrade the database with that revision every time you change them. From the `backend` directory, use `uv` to run Alembic against the PostgreSQL container:

* Alembic is already configured to import your SQLModel models from `./backend/app/models.py`.

* After changing a model (for example, adding a column), create a revision:

```console
uv run alembic revision --autogenerate -m "Add column last_name to User model"
```

* Commit to the git repository the files generated in the alembic directory.

* After creating the revision, run the migration in the database (this is what will actually change the database):

```console
uv run alembic upgrade head
```

If you don't want to use migrations at all, uncomment the lines in the file at `./backend/app/core/db.py` that end in:

```python
SQLModel.metadata.create_all(engine)
```

and comment the migration line in the `justfile` `prestart` recipe.

If you don't want to start with the default models and want to remove them / modify them, from the beginning, without having any previous revision, you can remove the revision files (`.py` Python files) under `./backend/app/alembic/versions/`. And then create a first migration as described above.

## Email Templates

The email templates are written with [React Email](https://react.email) in `./packages/react-email/`. The `emails` directory holds one component per email and the `ui` directory holds the shared components (layout, heading, button, link, callout).

The rendered HTML in `./backend/app/email-templates/` is generated from those components. It is what the application sends and should not be edited by hand.

To preview the emails while editing them, start the dev server from the root of the project:

```console
bun run email:dev
```

Values coming from the backend are declared as Jinja placeholders in the component props, for example `username = "{{ username }}"`. The context for each email is built in `generate_*_email()` in `./backend/app/utils.py`, so a new placeholder needs to be added there too.

Once you are done, regenerate the templates used by the application:

```console
bun run email:export
```
