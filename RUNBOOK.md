# Runbook: In Case of Emergency

This guide describes what to do when an alert fires for the MLH URL Shortener service.

---

## Alert 1: Service Down

**What it means:** The `/health` endpoint returned a non-200 response, meaning the application cannot reach the database.

### Immediate Steps

1. Check the alert dashboard: `http://localhost:5000/alerts`
2. Check recent logs: `http://localhost:5000/logs`
3. Check container status:
   ```
   docker compose ps
   ```

### Diagnosis

Check the app container logs for database connection errors:
```
docker compose logs app --tail 50
```

Check the database container logs:
```
docker compose logs db --tail 50
```

Check if the database container is healthy:
```
docker compose ps db
```

### Resolution

**If the database container is down or unhealthy:**
```
docker compose restart db
```
Wait for the health check to pass, then verify:
```
curl http://localhost:5000/health
```

**If the app container is down:**
```
docker compose restart app
```

**If both containers are down:**
```
docker compose up -d
```

**If the issue persists**, check disk space and memory on the host — a full disk can prevent Postgres from writing.

### Escalation

If the service does not recover after restarting containers, check Datadog APM at `https://us3.datadoghq.com/apm/services` for trace-level errors and escalate to the project owner.

---

## Alert 2: High Error Rate

**What it means:** More than 10% of recent requests returned a 5xx status code.

### Immediate Steps

1. Check the alert dashboard: `http://localhost:5000/alerts`
2. Check recent logs for errors: `http://localhost:5000/logs`
3. Check Datadog traces for the failing endpoint: `https://us3.datadoghq.com/apm/traces`

### Diagnosis

Look at `/logs` and identify which endpoint is returning 5xx errors. The log format is:
```
{"level": "ERROR", "message": "POST /shorten 500 (12ms)", "timestamp": "..."}
```

Check the app container logs for Python exceptions:
```
docker compose logs app --tail 100
```

Filter for errors specifically:
```
docker compose logs app 2>&1 | grep -i "error\|exception\|traceback"
```

### Resolution

**If the database is causing errors** (e.g. connection pool exhausted):
```
docker compose restart db
docker compose restart app
```

**If a bad deployment caused the errors**, roll back to the previous image:
```
docker compose down
git revert HEAD
docker compose up --build -d
```

**If errors are caused by bad input or an external issue**, investigate the specific endpoint in Datadog traces and fix the underlying code.

### Escalation

If the error rate does not drop within 5 minutes of restarting the service, escalate and consider taking the service offline to prevent further errors.

---

## Alert 3: High CPU Usage

**What it means:** CPU usage has been above 90% for 2 or more consecutive minutes.

### Immediate Steps

1. Check the alert dashboard: `http://localhost:5000/alerts` — the CPU card shows current usage
2. Check current metrics: `http://localhost:5000/metrics`
3. Check which process is consuming CPU:
   ```
   docker stats
   ```

### Diagnosis

Identify which container is using the most CPU:
```
docker stats --no-stream
```

Check if the app is handling an unusual volume of requests:
```
docker compose logs app --tail 100
```

Check Datadog for traffic spikes: `https://us3.datadoghq.com/apm/services`

### Resolution

**If a traffic spike is causing high CPU**, it should resolve on its own once traffic normalises. Monitor the dashboard.

**If the app container is in a runaway state:**
```
docker compose restart app
```

**If the database is causing high CPU** (e.g. a slow query loop):
```
docker compose restart db
```

**If high CPU persists after restarting**, check for any background scripts or cron jobs running on the host machine consuming resources.

### Escalation

If CPU remains above 90% for more than 10 minutes after investigation, escalate to the project owner and consider scaling the service or reducing traffic.

---

## General Commands Reference

| Task | Command |
|------|---------|
| Check all container status | `docker compose ps` |
| View app logs | `docker compose logs app` |
| View database logs | `docker compose logs db` |
| Restart app | `docker compose restart app` |
| Restart database | `docker compose restart db` |
| Restart everything | `docker compose up -d` |
| Full rebuild | `docker compose up --build -d` |
| Check live metrics | `curl http://localhost:5000/metrics` |
| Check health | `curl http://localhost:5000/health` |
| Check recent logs | `curl http://localhost:5000/logs?lines=50` |
| View alert dashboard | `http://localhost:5000/alerts` |
| View Datadog traces | `https://us3.datadoghq.com/apm/traces` |
