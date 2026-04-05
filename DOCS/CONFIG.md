# Configuration Reference

All configuration is done through environment variables. Copy `.env.example` to `.env` and edit it before starting the app.

```bash
cp .env.example .env
```

---

## Environment Variables

| Variable            | Default        | Required | Description                                      |
|---------------------|----------------|----------|--------------------------------------------------|
| `DATABASE_NAME`     | `hackathon_db` | Yes      | Name of the PostgreSQL database                  |
| `DATABASE_HOST`     | `localhost`    | Yes      | Hostname or IP of the PostgreSQL server          |
| `DATABASE_PORT`     | `5432`         | Yes      | Port the PostgreSQL server listens on            |
| `DATABASE_USER`     | `postgres`     | Yes      | PostgreSQL user to authenticate as               |
| `DATABASE_PASSWORD` | `postgres`     | Yes      | Password for the PostgreSQL user                 |
| `FLASK_DEBUG`       | `false`        | No       | Set to `true` to enable Flask debug mode         |

---

## Variable Details

### `DATABASE_NAME`
The name of the PostgreSQL database the app connects to.

- Default: `hackathon_db`
- The database must already exist before starting the app (local setup) or will be created automatically by the `db` Docker service.
- To create it manually: `createdb -U postgres hackathon_db`

### `DATABASE_HOST`
Hostname or IP address of the PostgreSQL server.

- Default: `localhost` (for local development)
- When running via Docker Compose, set this to `db` (the name of the Postgres service) — Docker's internal DNS resolves it automatically. The `docker-compose.yml` already sets this correctly.

### `DATABASE_PORT`
Port that PostgreSQL listens on.

- Default: `5432` (PostgreSQL's standard port)
- Only change this if you're running Postgres on a non-standard port.

### `DATABASE_USER`
PostgreSQL username the app authenticates with.

- Default: `postgres`
- The user must have `CREATE TABLE`, `SELECT`, `INSERT`, and `DELETE` privileges on `DATABASE_NAME`.

### `DATABASE_PASSWORD`
Password for `DATABASE_USER`.

- Default: `postgres`
- **Change this in any environment that isn't purely local.** Do not commit a real password to `.env` in version control — `.env` is in `.gitignore`.

### `FLASK_DEBUG`
Enables Flask's debug mode, which provides:
- Automatic server reload on code changes
- Detailed error pages in the browser
- The interactive Werkzeug debugger

- Default: `false`
- **Never set this to `true` in production.** Debug mode exposes an interactive Python console that can execute arbitrary code on the server.

---

## Example Configurations

### Local development

```env
FLASK_DEBUG=true
DATABASE_NAME=hackathon_db
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
```

### Docker Compose

The `docker-compose.yml` sets these directly on the `app` service — no `.env` file is needed when running via Docker Compose:

```yaml
environment:
  - DATABASE_NAME=hackathon_db
  - DATABASE_HOST=db        # Docker internal hostname
  - DATABASE_PORT=5432
  - DATABASE_USER=postgres
  - DATABASE_PASSWORD=postgres
```

### CI (GitHub Actions)

The `ci.yml` workflow injects the variables as step-level `env` for the test run:

```yaml
env:
  DATABASE_NAME: hackathon_db
  DATABASE_HOST: localhost
  DATABASE_PORT: 5432
  DATABASE_USER: postgres
  DATABASE_PASSWORD: postgres
```

---

## Where variables are read

All six variables are read in `app/database.py` via `os.environ.get(...)` with the defaults shown above. None of the variables are required to be set if the defaults match your environment.

```python
# app/database.py
database = PostgresqlDatabase(
    os.environ.get("DATABASE_NAME", "hackathon_db"),
    host=os.environ.get("DATABASE_HOST", "localhost"),
    port=int(os.environ.get("DATABASE_PORT", 5432)),
    user=os.environ.get("DATABASE_USER", "postgres"),
    password=os.environ.get("DATABASE_PASSWORD", "postgres"),
)
```

`FLASK_DEBUG` is loaded by `python-dotenv` via `load_dotenv()` in `app/__init__.py` and is not explicitly read in application code — Flask picks it up from the environment automatically.
