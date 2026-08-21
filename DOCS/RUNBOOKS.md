# Runbooks

Step-by-step response guides for operational incidents and failure conditions in the URL Shortener multi-service fleet.

Each runbook follows a structured response format: **Trigger**, **Confirm**, **Diagnose**, **Fix**, and **Verify Recovery**.

---

## RB-01: Health Check Failing — Database Unreachable

**Trigger:** `GET /health` returns HTTP 503 with `{"status": "unavailable", "reason": "database unreachable"}`.

### 1. Confirm the Incident
```bash
curl http://localhost:5000/health
# Expected (broken): {"status": "unavailable", "reason": "database unreachable"}
```

### 2. Check Database Status
**Docker:**
```bash
docker compose ps db
docker compose logs db --tail=50
```

**Local (Native):**
```bash
pg_isready -U postgres -h localhost -p 5432
```

### 3. Restart Database Service
**Docker:**
```bash
docker compose restart db
# Wait for healthcheck to pass, then restart app replicas if needed:
docker compose restart app
```

**Local:**
```bash
# Linux
sudo systemctl restart postgresql

# macOS
brew services restart postgresql
```

### 4. Verify Recovery
```bash
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

---

## RB-02: App Returning HTTP 500 on All Requests

**Trigger:** Every endpoint returns `{"error": "internal server error"}` (HTTP 500).

### 1. Confirm the Incident
```bash
curl http://localhost:5000/health
curl http://localhost:5000/
# If all routes return 500, a global dependency or configuration error is present
```

### 2. Inspect Logs for Stack Traces
```bash
# Stream error logs across app replicas
docker compose logs app 2>&1 | grep -i -E "error|exception|traceback"
```

### 3. Common Causes & Fixes
| Log Exception | Cause | Resolution |
| :--- | :--- | :--- |
| `peewee.OperationalError` | PostgreSQL down | Follow **RB-01** |
| `ModuleNotFoundError` | Missing Python dependency | Rebuild images: `docker compose up -d --build --scale app=4` |
| `KeyError` / Missing Env | Missing required variable | Check `.env` against [CONFIG.md](CONFIG.md) |

### 4. Verify Recovery
```bash
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

---

## RB-03: Nginx 502 Bad Gateway / Upstream Connection Failure

**Trigger:** Clients accessing `http://localhost:5000` receive `HTTP 502 Bad Gateway`.

### 1. Confirm the Incident
```bash
curl -i http://localhost:5000/
# Returns: HTTP/1.1 502 Bad Gateway
```

### 2. Diagnose Nginx & App Replicas
1. Check Nginx error logs:
   ```bash
   docker compose logs nginx --tail=50
   # Look for: "connect() failed (111: Connection refused) while connecting to upstream"
   ```
2. Check if all backend `app` containers are down:
   ```bash
   docker compose ps
   ```

### 3. Resolution
1. Restart the backend application replica fleet:
   ```bash
   docker compose restart app
   ```
2. If Nginx cached stale upstream DNS records, reload Nginx:
   ```bash
   docker compose exec nginx nginx -s reload
   ```

### 4. Verify Recovery
```bash
curl -i http://localhost:5000/health
# Expected: HTTP/1.1 200 OK
```

---

## RB-04: Redis Cache Outage & Latency Degradation

**Trigger:** Latency spikes during high traffic, or `ConnectionError` warnings in application logs.

### 1. Diagnose Redis Status
1. Check Redis container health:
   ```bash
   docker compose ps redis
   ```
2. Test Redis ping responsiveness:
   ```bash
   docker compose exec redis redis-cli ping
   # Expected if healthy: PONG
   ```

### 2. Impact Analysis
The application features **graceful fallback**: if Redis is unreachable, read requests fall back to PostgreSQL automatically without throwing 500 errors to users. However, database read contention and request latency will increase.

### 3. Resolution
1. Restart the Redis service:
   ```bash
   docker compose restart redis
   ```
2. Inspect Redis logs:
   ```bash
   docker compose logs redis --tail=50
   ```

### 4. Verify Recovery
```bash
docker compose exec redis redis-cli ping
# Expected: PONG

# Verify new short codes are caching:
docker compose exec redis redis-cli keys "url:*"
```

---

## RB-05: Docker App Container in Restart Loop

**Trigger:** `docker compose ps` shows `app` containers in `Restarting` status.

### 1. Inspect Crash Logs
```bash
docker compose logs app --tail=100
```

### 2. Common Causes & Fixes
* **Dependency Health Checks Unmet:**
  `app` waits for both `db` and `redis` health checks. If either is starting slowly, allow 15 seconds or restart dependencies:
  ```bash
  docker compose restart db redis
  ```
* **Port 5000 Conflict on Host:**
  Port 5000 is bound by Nginx. Stop any conflicting local processes:
  ```bash
  # Linux/Mac
  lsof -i :5000 | awk 'NR>1 {print $2}' | xargs kill -9
  ```
* **Image Rebuild Needed:**
  ```bash
  docker compose up -d --build --scale app=4
  ```

### 3. Verify Recovery
```bash
docker compose ps
# All containers should report "Up" or "healthy"
```

---

## RB-06: Redirect Returns 404 for a Valid Short Code (Cache / DB Desync)

**Trigger:** `GET /<short_code>` returns `{"error": "short code not found"}` immediately after link creation.

### 1. Verify Database and Cache Records
1. Check PostgreSQL:
   ```bash
   docker compose exec db psql -U postgres hackathon_db -c "SELECT * FROM url WHERE short_code = '<short_code>';"
   ```
2. Check Redis in-memory key:
   ```bash
   docker compose exec redis redis-cli get "url:<short_code>"
   ```

### 2. Resolution
* **If row exists in DB but not Redis:**
  Visiting the URL will automatically re-populate Redis via read-through caching.
* **If stale or conflicting data exists in Redis:**
  Flush the in-memory cache to force a fresh synchronization from PostgreSQL:
  ```bash
  docker compose exec redis redis-cli flushall
  ```

### 3. Verify Recovery
```bash
curl -L http://localhost:5000/<short_code>
# Expected: 302 redirect to the destination URL
```

---

## RB-07: Short Code Collision — 500 on URL Creation

**Trigger:** `POST /shorten` returns HTTP 500 with `{"error": "could not generate a unique short code"}`.

### 1. Confirm the Collision Failure
```bash
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### 2. Check Database Record Count
```bash
docker compose exec db psql -U postgres hackathon_db -c "SELECT COUNT(*) FROM url;"
```
`secrets.token_urlsafe(6)` provides over 280 trillion combinations. Collisions at low record counts indicate database connection issues rather than namespace exhaustion.

### 3. Resolution
If namespace exhaustion occurs under massive volume:
1. Increase `MAX_RETRIES` (e.g. from 5 to 10) in `app/routes/urls.py`.
2. Increase short code token length in `secrets.token_urlsafe(8)`.
3. Redeploy the fleet: `docker compose up -d --build --scale app=4`.

---

## RB-08: Discord Webhook Alert Delivery Failure

**Trigger:** System error rates exceed thresholds but no alerts arrive in Discord.

### 1. Test Webhook Manually
```bash
curl -X POST http://localhost:5000/alerts/test
```
* **Returns `{"status": "ok"}`:** Webhook configuration and network egress are operational.
* **Returns `{"status": "error"}`:** Verify `DISCORD_WEBHOOK_URL` in `.env`.

### 2. Check Alert Cooldown
Inspect `alerts.yml` — a default 300-second (5-minute) cooldown window suppresses duplicate alerts during ongoing incidents. Check current alert state at `http://localhost:5000/alerts`.

---

## Emergency Commands Quick Reference

| Action | Command |
| :--- | :--- |
| **Check entire fleet status** | `docker compose ps` |
| **View logs across all services** | `docker compose logs -f` |
| **View app replica logs** | `docker compose logs -f app` |
| **View Nginx logs** | `docker compose logs -f nginx` |
| **Restart entire fleet** | `docker compose restart` |
| **Full rebuild & scale (4 instances)** | `docker compose up -d --build --scale app=4` |
| **Test Redis responsiveness** | `docker compose exec redis redis-cli ping` |
| **Flush Redis cache** | `docker compose exec redis redis-cli flushall` |
| **Dispatch test alert to Discord** | `curl -X POST http://localhost:5000/alerts/test` |
| **Check service health** | `curl http://localhost:5000/health` |
| **View live metrics** | `curl http://localhost:5000/metrics` |
