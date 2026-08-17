# URL Shortener — Project README

A high-concurrency, observable, and fault-tolerant URL shortening service built with Flask, Peewee ORM, PostgreSQL, Redis in-memory caching, Nginx load balancing, and Datadog APM monitoring.

Paste in a long URL, get a short link back. Click the short link, get redirected in sub-milliseconds.

---

## Architecture

```text
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                          Client                                           │
│                       (Browser, API consumer, or Locust Load Test)                        │
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │ HTTP Requests (Port 5000)
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Nginx Load Balancer (:80)                                 │
│                      Round-robin traffic distribution across replicas                     │
└───────────────┬─────────────────────────────┬─────────────────────────────┬───────────────┘
                │                             │                             │
                ▼                             ▼                             ▼
   ┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
   │    Flask App Replica 1    │ │    Flask App Replica 2    │ │    Flask App Replica N    │
   │  ┌─────────────────────┐  │ │  ┌─────────────────────┐  │ │  ┌─────────────────────┐  │
   │  │ Web UI & Alerts UI  │  │ │  │ Web UI & Alerts UI  │  │ │  │ Web UI & Alerts UI  │  │
   │  │ GET /   POST /      │  │ │  │ GET /   POST /      │  │ │  │ GET /   POST /      │  │
   │  │ GET /alerts         │  │ │  │ GET /alerts         │  │ │  │ GET /alerts         │  │
   │  ├─────────────────────┤  │ │  ├─────────────────────┤  │ │  ├─────────────────────┤  │
   │  │ JSON API & Metrics  │  │ │  │ JSON API & Metrics  │  │ │  │ JSON API & Metrics  │  │
   │  │ POST /shorten       │  │ │  │ POST /shorten       │  │ │  │ POST /shorten       │  │
   │  │ GET /health /metrics│  │ │  │ GET /health /metrics│  │ │  │ GET /health /metrics│  │
   │  │ GET /logs           │  │ │  │ GET /logs           │  │ │  │ GET /logs           │  │
   │  ├─────────────────────┤  │ │  ├─────────────────────┤  │ │  ├─────────────────────┤  │
   │  │ Redirect Handler    │  │ │  │ Redirect Handler    │  │ │  │ Redirect Handler    │  │
   │  │ GET /<short_code>   │  │ │  │ GET /<short_code>   │  │ │  │ GET /<short_code>   │  │
   │  └──────────┬──────────┘  │ │  └──────────┬──────────┘  │ │  └──────────┬──────────┘  │
   │             │             │ │             │             │ │             │             │
   │  ┌──────────▼──────────┐  │ │  ┌──────────▼──────────┐  │ │  ┌──────────▼──────────┐  │
   │  │ Datadog Tracer (APM)│  │ │  │ Datadog Tracer (APM)│  │ │  │ Datadog Tracer (APM)│  │
   │  │ (ddtrace-run)       │  │ │  │ (ddtrace-run)       │  │ │  │ (ddtrace-run)       │  │
   │  └─────────────────────┘  │ │  └─────────────────────┘  │ │  └─────────────────────┘  │
   └─────────────┬─────────────┘ └─────────────┬─────────────┘ └─────────────┬─────────────┘
                 │                             │                             │
        ┌────────┴─────────────────────────────┴─────────────────────────────┴────────┐
        │                                                                             │
        │ In-Memory Read/Write                                   Database Read/Write  │
        ▼                                                                             ▼
┌───────────────────────────────┐                             ┌───────────────────────────────┐
│         Redis (:6379)         │                             │      PostgreSQL (:5432)       │
│                               │                             │                               │
│  Key-Value Cache (1 hr TTL)   │                             │  Persistent Storage (url)     │
│  `url:<short_code>` ➔ URL     │                             │  `id, original_url, code`     │
└───────────────────────────────┘                             └───────────────────────────────┘
                                                                              ▲
                                                                              │
                                                              ┌───────────────┴───────────────┐
                                                              │     Datadog Agent Container   │
                                                              │  APM Traces, Metrics & StatsD │
                                                              └───────────────────────────────┘
```

**Request Flow:**

1. **Shorten URL (`POST /shorten` or `POST /`)**:
   - Client sends a URL.
   - Flask validates the URL (must start with `http://` or `https://`, length ≤ 2048 chars).
   - Generates a unique short code with collision retries.
   - Stores the mapping in **PostgreSQL** via Peewee ORM.
   - Immediately populates **Redis** (`url:<short_code>` ➔ `original_url`) via write-through caching.
   - Returns the short URL.

2. **Follow Short Link (`GET /<short_code>`)**:
   - Nginx balances the request to an available Flask replica.
   - Flask checks **Redis** first.
   - **Cache Hit (<1ms):** Returns `302 Found` redirect immediately from RAM without hitting PostgreSQL.
   - **Cache Miss:** Queries PostgreSQL, populates Redis, and issues `302 Found`.
   - If Redis is unavailable, the service automatically falls back to PostgreSQL queries gracefully.

---

## Prerequisites

| Requirement | Recommended Version | Notes |
| :--- | :--- | :--- |
| **Python** | `3.13` | Managed automatically by `uv` |
| **uv** | Latest | Fast Python package and environment manager |
| **Docker & Docker Compose** | Docker Desktop | Runs the multi-container fleet (Nginx, Redis, Postgres, Datadog) |
| **PostgreSQL** | `16+` | Included in Docker Compose or run locally |
| **Redis** | `7+` | Included in Docker Compose or run locally |

---

## Setup & Running

### Option 1: Docker (Recommended — Full Production Fleet)

Starts the complete fleet: Nginx load balancer, PostgreSQL database, Redis in-memory cache, Datadog Agent, and 4 scaled Flask application replicas.

```bash
# 1. Configure environment variables
cp .env.example .env

# 2. Build and launch all services with 4 app replicas
docker compose up -d --build --scale app=4

# 3. Verify health
curl http://localhost:5000/health
# Expected: {"status": "ok"}

# 4. View running fleet
docker ps

# 5. Stop all containers
docker compose down
```

### Option 2: Local Development (Native)

For testing and development outside Docker:

```bash
# 1. Install dependencies into virtual environment
uv sync

# 2. Configure .env
cp .env.example .env
# Ensure local PostgreSQL and Redis are running on localhost

# 3. Start the application
uv run python run.py
```

The application is accessible at **http://localhost:5000**.

---

## Environment Variables

All variables live in `.env` (copied from `.env.example`):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_NAME` | `hackathon_db` | PostgreSQL database name |
| `DATABASE_HOST` | `localhost` (local) / `db` (Docker) | PostgreSQL host address |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_USER` | `postgres` | PostgreSQL username |
| `DATABASE_PASSWORD` | `postgres` | PostgreSQL password |
| `REDIS_HOST` | `localhost` (local) / `redis` (Docker) | Redis cache host address |
| `REDIS_PORT` | `6379` | Redis cache port |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `DISCORD_WEBHOOK_URL`| *(Optional)* | Discord webhook for incident error rate alerts |
| `DD_API_KEY` | *(Optional)* | Datadog API key for APM and metrics collection |
| `DD_SITE` | `us3.datadoghq.com` | Datadog site intake URL |

---

## Project Structure

```text
mlh-production-engineering-hackathon-proj/
├── app/
│   ├── __init__.py          # App factory (create_app), request timing, global error handlers
│   ├── alerts.py            # Discord webhook dispatcher, sliding-window error rate calculator
│   ├── cache.py             # Redis client initialization and configuration
│   ├── database.py          # DatabaseProxy, BaseModel, Peewee connection lifecycle
│   ├── logging.py           # Structured request logging configuration
│   ├── models/
│   │   ├── __init__.py      # Model exports
│   │   └── url.py           # Url Peewee model (original_url, short_code, created_at)
│   ├── routes/
│   │   ├── __init__.py      # Blueprint registration
│   │   ├── alerts.py        # /alerts UI and /alerts/test webhook trigger endpoint
│   │   ├── debug.py         # Debugging routes
│   │   ├── logs.py          # /logs endpoint for recent access history
│   │   ├── metrics.py       # /metrics endpoint (request counts, latency, memory/CPU)
│   │   └── urls.py          # URL shortener, redirect handler, Redis read/write cache
│   └── templates/
│       ├── alerts.html      # Incident response & alerts dashboard
│       └── index.html       # Web UI for creating and managing short links
├── tests/
│   ├── test_alerts.py       # Alert threshold, sliding window, and webhook tests
│   ├── test_bonus.py        # Edge cases (malformed input, collisions, scheme validation)
│   ├── test_cache.py        # Redis cache hits, misses, and DB fallback unit tests
│   ├── test_integration.py  # Database state & Peewee integration tests
│   ├── test_logs.py         # Request log formatting and duration tracking tests
│   ├── test_metrics.py      # Metrics collection and calculation tests
│   └── test_urls.py         # Functional route tests for core URL shortener flows
├── scripts/
│   └── trigger_high_error_rate.py # Incident simulation script to trigger Discord alerts
├── Hackathon_Quests/        # Quest documentation, verification screenshots, bottleneck report
├── alerts.yml               # Threshold rules and cooldown configuration for alerts
├── docker-compose.yml       # Production fleet: Nginx, App replicas, Redis, Postgres, Datadog
├── Dockerfile               # Production container definition (Python 3.13-slim + uv)
├── locustfile.py            # Locust load test suite for 50, 200, and 500 concurrent users
├── nginx.conf               # Nginx reverse proxy and upstream round-robin load balancer config
├── pyproject.toml           # Project dependencies (Flask, Peewee, Redis, Locust, ddtrace, pytest)
├── .env.example             # Environment template
└── run.py                   # Development entrypoint
```

---

## API Reference

### Core URL Shortener Routes

#### `POST /shorten`
Shortens a URL programmatically via JSON API.

* **Request:**
  ```json
  POST /shorten
  Content-Type: application/json

  {
    "url": "https://www.example.com/very/long/url/path"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "short_code": "xGIUqq",
    "short_url": "http://localhost:5000/xGIUqq"
  }
  ```
* **Response (400 Bad Request):**
  ```json
  {
    "error": "a valid url is required (must start with http:// or https://)"
  }
  ```

---

#### `GET /<short_code>`
Resolves the short code and redirects the client to the original destination. Served directly from Redis RAM in <1ms on cache hits.

* **Response (302 Found):**
  ```text
  HTTP/1.1 302 Found
  Location: https://www.example.com/very/long/url/path
  ```
* **Response (404 Not Found):**
  ```json
  {
    "error": "short code not found"
  }
  ```

---

#### `GET /` & `POST /`
Serves the browser Web UI and handles standard form submissions.

---

### Observability & Management Routes

#### `GET /health`
Verifies that the application can reach the database.
* **Response (200 OK):** `{"status": "ok"}`
* **Response (503 Service Unavailable):** `{"status": "unavailable", "reason": "database unreachable"}`

#### `GET /metrics`
Returns application metrics, request statistics, latency percentiles, and system resource utilization.

#### `GET /logs`
Returns the recent structured access logs with response times and HTTP status codes.

#### `GET /alerts` & `POST /alerts/test`
- `GET /alerts`: Renders the Alert Management Dashboard displaying error rate statistics and trigger history.
- `POST /alerts/test`: Dispatches a sample incident alert to the configured `DISCORD_WEBHOOK_URL`.

---

## Reliability, Monitoring & Alerting

### 1. Alerting System (`app/alerts.py` & `alerts.yml`)
- Tracks error rates in a sliding request window.
- Automatically dispatches alert payloads with system diagnostics to Discord when error rates exceed threshold rules.
- Includes a cooldown window to prevent webhook spamming during sustained incidents.

### 2. Datadog APM & Metrics
- The Docker fleet includes the official Datadog Agent container (`agent:7`).
- Flask services run wrapped in `ddtrace-run`, tracing database query durations, HTTP latency, and Redis cache operations automatically.

---

## Testing & Benchmarks

### 1. Automated Test Suite (Pytest)
Run all 54 unit and integration tests across the 7 test modules:

```bash
# Run all tests
uv run pytest tests/ -v

# Run with test coverage report
uv run pytest tests/ -v --cov=app --cov-report=term-missing
```

### 2. High-Concurrency Load Testing (Locust)
Stress test the load balanced fleet:

```bash
# 500 Concurrent Users
uv run locust -f locustfile.py --headless -u 500 -r 50 --run-time 1m --host http://localhost:5000
```

**Benchmark Results:**
- **Concurrency:** 500 concurrent users
- **Throughput:** 242.1 requests / second
- **Stability:** 0.0% failure rate (0 errors across 13,546+ requests)
- **Latency (p95):** 210 ms
