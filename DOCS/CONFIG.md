# Configuration Reference

All runtime and infrastructure settings for the URL Shortener service are managed via environment variables and dedicated configuration files.

Copy `.env.example` to `.env` and edit it before starting the application:

```bash
cp .env.example .env
```

---

## 1. Environment Variables

| Variable | Default | Required | Description |
| :--- | :--- | :--- | :--- |
| **`DATABASE_NAME`** | `hackathon_db` | Yes | Name of the PostgreSQL database |
| **`DATABASE_HOST`** | `localhost` (local) / `db` (Docker) | Yes | Hostname or IP of the PostgreSQL server |
| **`DATABASE_PORT`** | `5432` | Yes | Port the PostgreSQL server listens on |
| **`DATABASE_USER`** | `postgres` | Yes | PostgreSQL user to authenticate as |
| **`DATABASE_PASSWORD`** | `postgres` | Yes | Password for the PostgreSQL user |
| **`REDIS_HOST`** | `localhost` (local) / `redis` (Docker) | Yes | Hostname or IP of the Redis caching server |
| **`REDIS_PORT`** | `6379` | Yes | Port the Redis caching server listens on |
| **`FLASK_DEBUG`** | `false` | No | Set to `true` to enable Flask debug mode (local only) |
| **`DISCORD_WEBHOOK_URL`**| *(Empty)* | No | Discord webhook endpoint for incident error alerts |
| **`DD_API_KEY`** | *(Empty)* | No | Datadog API authentication key for APM & metrics |
| **`DD_SITE`** | `us3.datadoghq.com` | No | Datadog site intake region URL |

---

## 2. Variable Details

### Database Configuration
* **`DATABASE_NAME`**: The PostgreSQL database name. Created automatically in Docker or via `createdb -U postgres hackathon_db` for local setups.
* **`DATABASE_HOST`**: Set to `localhost` when running native Python processes, or `db` when running within the Docker Compose network.
* **`DATABASE_PORT`**: Standard PostgreSQL port (`5432`).
* **`DATABASE_USER` & `DATABASE_PASSWORD`**: Credentials for PostgreSQL connection authentication.

### Cache Configuration
* **`REDIS_HOST`**: Hostname of the Redis in-memory cache. Set to `localhost` for native runs, or `redis` for Docker Compose.
* **`REDIS_PORT`**: Standard Redis port (`6379`).

### Application & Observability
* **`FLASK_DEBUG`**: Enables Flask's interactive debugger and auto-reloader. Keep `false` in production environments.
* **`DISCORD_WEBHOOK_URL`**: Webhook URL used by `app/alerts.py` to send automated diagnostic alerts when error rates exceed defined thresholds.
* **`DD_API_KEY` & `DD_SITE`**: Configures the Datadog Agent container to securely stream APM traces, latency percentiles, and infrastructure metrics to your Datadog dashboard.

---

## 3. Example Configurations

### Local Development (`.env`)
```env
# Flask
FLASK_DEBUG=true

# PostgreSQL
DATABASE_NAME=hackathon_db
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Observability & Alerting (Optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DD_API_KEY=your_datadog_api_key
DD_SITE=us3.datadoghq.com
```

### Docker Compose (`docker-compose.yml`)
The `docker-compose.yml` passes internal network names directly to containers while pulling secrets from `.env`:

```yaml
services:
  app:
    environment:
      - DATABASE_NAME=hackathon_db
      - DATABASE_HOST=db
      - DATABASE_PORT=5432
      - DATABASE_USER=postgres
      - DATABASE_PASSWORD=postgres
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - FLASK_DEBUG=false
      - DD_TRACE_AGENT_URL=unix:///var/run/datadog/apm.socket
      - DD_DOGSTATSD_URL=unix:///var/run/datadog/dsd.socket
      - DD_SERVICE=mlh-hackathon
      - DD_ENV=production
      - DD_VERSION=1.0

  datadog:
    environment:
      - DD_API_KEY=${DD_API_KEY}
      - DD_SITE=${DD_SITE}
      - DD_APM_ENABLED=true
```

---

## 4. Where Variables are Read in Code

Configuration loading is modularized across specialized subsystems:

| File | Variables Consumed | Purpose |
| :--- | :--- | :--- |
| **`app/database.py`** | `DATABASE_*` | Establishes Peewee ORM connection pool to PostgreSQL |
| **`app/cache.py`** | `REDIS_HOST`, `REDIS_PORT` | Initializes thread-safe Redis client instance |
| **`app/alerts.py`** | `DISCORD_WEBHOOK_URL` | Authenticates webhook requests to Discord |
| **`app/__init__.py`** | `FLASK_DEBUG` | Configures logging level and debugging mode |
| **`Dockerfile` / Compose** | `DD_*` | Passed to `ddtrace-run` and Datadog Agent container |

---

## 5. File-Based Configuration

In addition to environment variables, system behavior is governed by two root configuration files:

### 1. `alerts.yml` (Incident Alerting Thresholds)
Defines rules for the automated error rate detector:
```yaml
error_rate:
  threshold_pct: 10.0     # Alert fires if error rate exceeds 10%
  window_size: 50         # Evaluated over a sliding window of 50 requests
  cooldown_seconds: 300   # 5-minute cooldown between repeated alerts
```

### 2. `nginx.conf` (Load Balancer & Upstream Routing)
Defines reverse proxy routing and connection concurrency:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream app_servers {
        server app:5000;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://app_servers;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```
