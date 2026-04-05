# Troubleshooting Guide

Common problems and how to fix them.

---

## Database connection errors

### Symptom
App fails to start, or `/health` returns `{"status": "unavailable", "reason": "database unreachable"}`.

Typical error in logs:
```
peewee.OperationalError: could not connect to server: Connection refused
```

### Causes and fixes

**PostgreSQL isn't running.**

```bash
# Check if it's up (Linux/Mac)
pg_isready -U postgres

# Start it (Mac with Homebrew)
brew services start postgresql

# Start it (Linux systemd)
sudo systemctl start postgresql

# Docker
docker compose up -d db
```

**Wrong credentials or host in `.env`.**

Open `.env` and confirm `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, and `DATABASE_PASSWORD` match your Postgres setup. See [CONFIG.md](CONFIG.md) for all variables and their defaults.

**Database doesn't exist yet.**

```bash
createdb -U postgres hackathon_db
```

**Docker: app container started before the database was ready.**

```bash
docker compose down
docker compose up -d
```

The `app` service has `depends_on: db: condition: service_healthy`, so it waits for `pg_isready` to pass. If you see this in a fresh `up`, it usually means Postgres took longer than expected — running `up` again after the db is healthy resolves it.

---

## Port already in use

### Symptom
```
OSError: [Errno 98] Address already in use
```

### Fix

Find what's using port 5000 and stop it, or run the app on a different port.

```bash
# Find the process
lsof -i :5000          # Mac/Linux
netstat -ano | findstr 5000   # Windows

# Kill it (replace <PID> with the number from above)
kill <PID>
```

To run on a different port, set the port in `run.py`:
```python
app.run(debug=True, port=5001)
```

---

## Short code returns 404 after creation

### Symptom
The app displays a short URL after submitting a link, but clicking it returns:
```json
{"error": "short code not found"}
```

### Fix

This is most commonly caused by a stale server process that didn't pick up the latest code, or a failed database write that wasn't surfaced. Steps to diagnose:

1. **Confirm the database is reachable:** `curl http://localhost:5000/health`
2. **Restart the server** — in development, the auto-reloader occasionally gets into a bad state.
3. **Check for database write errors** in the server logs. If `create_url` is silently failing after max retries, the response will still render but won't have a record backing it.

---

## App returns HTTP 500 on every request

### Symptom
All endpoints return:
```json
{"error": "internal server error"}
```

### Fix

1. Check the server logs for the actual exception — Flask logs the traceback to stderr.
2. Common causes:
   - Environment variable missing or misconfigured (see [CONFIG.md](CONFIG.md))
   - Database connection lost mid-request (restart Postgres, then the app)
   - Import error due to a missing dependency — run `uv sync` to reinstall

---

## `uv sync` fails or packages won't install

### Symptom
```
error: No solution found when resolving dependencies
```
or missing module errors when running the app.

### Fix

```bash
# Ensure you're on Python 3.13
python --version

# Remove the virtual environment and reinstall from scratch
rm -rf .venv
uv sync
```

---

## Docker: app container keeps restarting

### Symptom
`docker compose ps` shows the `app` container in a restart loop.

### Fix

```bash
# Inspect the logs for the actual error
docker compose logs app

# Common causes:
# - DATABASE_PASSWORD mismatch between app and db services
# - Port 5000 already in use on the host
# - Corrupt image — rebuild it
docker compose up -d --build
```

---

## Docker: database volume has stale/corrupt data

### Symptom
Postgres won't start, or the app crashes with schema errors after a code change.

### Fix

**Warning: this deletes all stored URLs.**

```bash
docker compose down -v   # removes the postgres_data volume
docker compose up -d     # starts fresh with a clean database
```

---

## Tests fail with database errors

### Symptom
```
peewee.OperationalError: ...
```
during `uv run pytest`.

### Fix

Tests require a running PostgreSQL instance. Set the following environment variables before running tests (or add them to your shell):

```bash
export DATABASE_NAME=hackathon_db
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_USER=postgres
export DATABASE_PASSWORD=postgres
```

Then rerun:
```bash
uv run pytest tests/ -v
```

In CI, these variables are injected automatically by the GitHub Actions workflow.
