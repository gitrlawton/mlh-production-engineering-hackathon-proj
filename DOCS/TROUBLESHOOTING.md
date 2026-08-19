# Troubleshooting Guide

Common issues, failure diagnostics, and step-by-step solutions for the URL Shortener service and its multi-container fleet.

---

## 1. Nginx & Load Balancing Issues

### Symptom: `HTTP 502 Bad Gateway`
When opening `http://localhost:5000`, Nginx returns a 502 Bad Gateway error page.

### Causes & Fixes
* **All backend `app` containers are down or still starting:**
  Nginx cannot establish a connection to the upstream `app:5000` service.
  ```bash
  # Check container status across all replicas
  docker compose ps

  # Check logs for the app replicas
  docker compose logs app
  ```
* **Database or Redis health check is blocking app startup:**
  The `app` containers wait for both `db` and `redis` to be healthy before booting. If either service is unhealthy, the app containers will not start.
  ```bash
  docker compose logs db
  docker compose logs redis
  ```

---

### Symptom: Port 5000 Already in Use
```text
Error response from daemon: driver failed programming external connectivity on endpoint ... Bind for 0.0.0.0:5000 failed: port is already allocated
```

### Causes & Fixes
Another process or older container is already listening on host port `5000`.

1. **Find and stop the conflicting process:**
   ```bash
   # Linux / macOS
   lsof -i :5000
   kill -9 <PID>

   # Windows (PowerShell)
   Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess | Stop-Process
   ```
2. **Or re-map Nginx to an alternate host port in `docker-compose.yml`:**
   ```yaml
   nginx:
     ports:
       - "5001:80"  # Changes host entrypoint to http://localhost:5001
   ```

---

## 2. Redis & Caching Issues

### Symptom: Slow Redirects or Redis Connection Warnings in Logs
```text
redis.exceptions.ConnectionError: Error connecting to redis:6379. Connection refused.
```

### Causes & Fixes
The application is designed with **graceful cache degradation**: if Redis goes down, the app automatically falls back to PostgreSQL without crashing, but latency will increase under heavy traffic.

1. **Verify the Redis container is running and healthy:**
   ```bash
   docker compose ps redis
   ```
2. **Test Redis responsiveness:**
   ```bash
   docker compose exec redis redis-cli ping
   # Expected response: PONG
   ```
3. **Inspect cached keys:**
   ```bash
   docker compose exec redis redis-cli keys "url:*"
   ```
4. **Flush stale or invalid cache data:**
   ```bash
   docker compose exec redis redis-cli flushall
   ```

---

## 3. Database Connection Errors

### Symptom: `/health` returns `503 Service Unavailable`
```json
{"status": "unavailable", "reason": "database unreachable"}
```
Or in the application logs:
```text
peewee.OperationalError: could not connect to server: Connection refused
```

### Causes & Fixes
1. **PostgreSQL container is stopped or unhealthy:**
   ```bash
   # Check PostgreSQL logs
   docker compose logs db

   # Restart the database container
   docker compose restart db
   ```
2. **Incorrect database credentials in `.env`:**
   Ensure `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, and `DATABASE_PASSWORD` match your environment. In Docker, `DATABASE_HOST` must be `db` (not `localhost`).
3. **Local development database missing:**
   If running locally outside Docker, create the database manually:
   ```bash
   createdb -U postgres hackathon_db
   ```

---

## 4. Docker App Container Crash / Restart Loops

### Symptom: `docker compose ps` shows `app` restarting continuously

### Causes & Fixes
1. **Inspect logs for the specific stack trace:**
   ```bash
   docker compose logs -f app
   ```
2. **Missing Python dependency in the image:**
   If dependencies in `pyproject.toml` changed, rebuild the container image:
   ```bash
   docker compose up -d --build --scale app=4
   ```
3. **Stale/Corrupted PostgreSQL Volume:**
   If database schemas became corrupted during local development:
   ```bash
   # Warning: deletes local database volume data
   docker compose down -v
   docker compose up -d --build --scale app=4
   ```

---

## 5. Discord Webhook & Alerting Issues

### Symptom: Automated Error Alerts Not Appearing in Discord

### Causes & Fixes
1. **Missing or invalid webhook URL:**
   Confirm `DISCORD_WEBHOOK_URL` is populated in `.env`.
2. **Test webhook delivery directly:**
   ```bash
   curl -X POST http://localhost:5000/alerts/test
   ```
   * If this returns `{"status": "ok"}`, the webhook URL and network egress are working.
   * If this returns an error, verify the Discord webhook URL channel permissions.
3. **Alert Cooldown Period Active:**
   To prevent channel spamming during prolonged outages, `alerts.yml` enforces a cooldown window (default: 5 minutes) between repeated notifications.

---

## 6. Datadog APM & Metrics Issues

### Symptom: Datadog Agent Logging API Key Errors

### Causes & Fixes
* **Missing `DD_API_KEY`:**
  If you do not have a Datadog API key, the core application will continue serving traffic normally. Datadog agent log warnings can be ignored during offline development.
* **Intake Site Mismatch:**
  Verify that `DD_SITE` in `.env` matches your Datadog account region (e.g. `us3.datadoghq.com`, `datadoghq.com`, `datadoghq.eu`).

---

## 7. Short Code Returns 404 After Creation

### Symptom
Submitting a URL generates a short code, but visiting `http://localhost:5000/<short_code>` returns:
```json
{"error": "short code not found"}
```

### Causes & Fixes
1. **Database Write Failure:**
   If PostgreSQL was briefly unreachable or unique code collision retries were exhausted, check `docker compose logs app` for database write exceptions.
2. **Redis / DB Desynchronization:**
   If a short code was deleted from PostgreSQL directly, it may still exist in Redis or vice versa. Flush Redis cache to force database synchronization:
   ```bash
   docker compose exec redis redis-cli flushall
   ```

---

## 8. Test Failures (`uv run pytest`)

### Symptom: Database connection error during test runs

### Causes & Fixes
Tests run in your local Python environment and connect to PostgreSQL at `DATABASE_HOST=localhost:5432` by default.

1. Ensure a PostgreSQL instance is running and accessible on port `5432`.
2. Ensure environment variables are loaded:
   ```bash
   cp .env.example .env
   ```
3. Run the test suite:
   ```bash
   uv run pytest tests/ -v
   ```
