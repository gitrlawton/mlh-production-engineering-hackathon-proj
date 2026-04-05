# Runbooks

Step-by-step response guides for specific failure conditions. Each runbook follows the same structure: what triggered it, how to confirm, how to fix, and how to verify recovery.

---

## RB-01: Health Check Failing — Database Unreachable

**Alert condition:** `GET /health` returns HTTP 503 with `{"status": "unavailable", "reason": "database unreachable"}`

### 1. Confirm the alert

```bash
curl http://localhost:5000/health
# Expected (broken): {"status": "unavailable", "reason": "database unreachable"}
```

### 2. Check if PostgreSQL is running

**Local:**
```bash
pg_isready -U postgres -h localhost -p 5432
# "no response" or "Connection refused" confirms Postgres is down
```

**Docker:**
```bash
docker compose ps
# Look for the "db" service — it should be "healthy"
docker compose logs db --tail=50
```

### 3. Restart PostgreSQL

**Local (Linux systemd):**
```bash
sudo systemctl restart postgresql
```

**Local (Mac/Homebrew):**
```bash
brew services restart postgresql
```

**Docker:**
```bash
docker compose restart db
# Wait ~15 seconds for the health check to pass, then restart app
docker compose restart app
```

### 4. Verify recovery

```bash
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

### 5. If Postgres is running but still unreachable

Check that `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, and `DATABASE_PASSWORD` in `.env` (or `docker-compose.yml`) match the running instance. See [CONFIG.md](CONFIG.md).

---

## RB-02: App Returning HTTP 500 on All Requests

**Alert condition:** Every endpoint returns `{"error": "internal server error"}` (HTTP 500).

### 1. Confirm the alert

```bash
curl http://localhost:5000/health
curl http://localhost:5000/
# Both returning 500 confirms it's not route-specific
```

### 2. Inspect application logs

**Local:**
```
The traceback is printed to stderr in the terminal where you ran `uv run run.py`.
```

**Docker:**
```bash
docker compose logs app --tail=100
```

Look for the Python exception and traceback — this will identify the root cause.

### 3. Common causes and fixes

| Log message | Fix |
|---|---|
| `OperationalError: could not connect to server` | Database is down — follow RB-01 |
| `ModuleNotFoundError` | Run `uv sync` to reinstall dependencies |
| `KeyError` / `AttributeError` on startup | Missing or malformed environment variable — check `.env` against [CONFIG.md](CONFIG.md) |

### 4. Restart the app after fixing

**Local:**
```bash
# Stop the running process (Ctrl+C), then:
uv run run.py
```

**Docker:**
```bash
docker compose up -d --build
```

### 5. Verify recovery

```bash
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

---

## RB-03: Short Code Collision — 500 on URL Shortening

**Alert condition:** `POST /shorten` returns HTTP 500 with `{"error": "could not generate a unique short code"}`.

This means all 5 retry attempts to generate a unique short code collided with existing records.

### 1. Confirm the alert

```bash
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# Returns: {"error": "could not generate a unique short code"}
```

### 2. Check how many URLs are stored

Connect to the database and count records:

```bash
psql -U postgres hackathon_db -c "SELECT COUNT(*) FROM url;"
```

`secrets.token_urlsafe(6)` produces ~281 trillion possible codes. Repeated 500s at low record counts suggest a code generator issue, not true exhaustion.

### 3. Check for database write errors

Inspect logs for `IntegrityError` or connection errors that are being silently swallowed during retries:

```bash
# Docker
docker compose logs app --tail=50
```

### 4. If the database is healthy and codes are genuinely exhausted

Increase the retry count in `app/routes/urls.py`:

```python
MAX_RETRIES = 5   # increase to 10 or more
```

Or increase the short code length in `create_url()`:

```python
short_code = secrets.token_urlsafe(8)  # was 6 — more entropy, fewer collisions
```

Deploy the change using the deploy guide: [DEPLOY.md](DEPLOY.md).

### 5. Verify recovery

```bash
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# Expected: HTTP 201 with short_code and short_url
```

---

## RB-04: Docker App Container in Restart Loop

**Alert condition:** `docker compose ps` shows the `app` container restarting repeatedly.

### 1. Confirm the alert

```bash
docker compose ps
# "app" shows Restarting or a high restart count
```

### 2. Read the crash logs

```bash
docker compose logs app --tail=50
```

### 3. Common causes and fixes

**Database not ready yet (race condition on fresh start):**
```bash
docker compose down
docker compose up -d
# The depends_on health check should handle this; if it doesn't, run `up` again after `db` is healthy
```

**Port 5000 already occupied on the host:**
```bash
lsof -i :5000          # Mac/Linux
netstat -ano | findstr 5000   # Windows
# Kill the occupying process, then:
docker compose up -d
```

**Corrupt or missing image:**
```bash
docker compose up -d --build
```

**Environment variable misconfiguration:**
Check `docker-compose.yml` environment block against [CONFIG.md](CONFIG.md).

### 4. Verify recovery

```bash
docker compose ps
# "app" should show "running" or "healthy"
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

---

## RB-05: Redirect Returns 404 for a Valid Short Code

**Alert condition:** `GET /<short_code>` returns `{"error": "short code not found"}` immediately after a short URL was created.

### 1. Confirm the alert

```bash
# Create a short URL
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# Copy the short_code from the response

# Immediately follow it
curl -i http://localhost:5000/<short_code>
# If it returns 404, the bug is confirmed
```

### 2. Verify the record exists in the database

```bash
psql -U postgres hackathon_db \
  -c "SELECT * FROM url WHERE short_code = '<short_code>';"
```

- **Row found:** The app is not reading from the database correctly — check connection config.
- **No row found:** The write was not committed. This may indicate a transaction or connection lifecycle issue.

### 3. Fix

Restart the application server to clear any stale connection state:

**Local:** Stop the process (Ctrl+C) and rerun `uv run run.py`.

**Docker:** `docker compose restart app`

### 4. Verify recovery

Shorten a new URL and immediately follow it:

```bash
curl -L http://localhost:5000/<new_short_code>
# Expected: 302 redirect to the original URL
```
