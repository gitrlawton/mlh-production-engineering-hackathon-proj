# Deploy Guide

How to get the URL Shortener service running, scale it under load, and safely roll back if something goes wrong.

---

## Deployment Options

There are two supported ways to run this application:

| Option | When to use |
| :--- | :--- |
| **[Docker Compose](#docker-deployment) (Recommended)** | Production, staging, and high-concurrency environments with load balancing and caching |
| **[Local (no Docker)](#local-deployment)** | Development, debugging, and local unit testing |

---

## Docker Deployment (Recommended)

Docker Compose manages the complete multi-service production fleet:
- **Nginx**: Reverse proxy and round-robin load balancer listening on port `5000`.
- **App Replicas**: Multiple independent Flask application containers running with Datadog APM tracing.
- **Redis**: In-memory cache for sub-millisecond redirect lookups.
- **PostgreSQL**: Persistent relational database for URL records.
- **Datadog Agent**: Background collector for APM traces, latency metrics, and container statistics.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd mlh-production-engineering-hackathon-proj

# 2. Configure environment variables
cp .env.example .env
# Edit .env to supply optional Datadog API keys or Discord webhook URLs if desired

# 3. Build and start the complete fleet with 4 scaled app replicas
docker compose up -d --build --scale app=4

# 4. Verify service health
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

The `app` containers wait for both the `db` (PostgreSQL) and `redis` containers to pass their health checks before starting, ensuring dependencies are fully operational.

### Useful Docker Commands

```bash
# View live logs across all services
docker compose logs -f

# View live logs from the scaled app containers only
docker compose logs -f app

# View live logs from Nginx load balancer
docker compose logs -f nginx

# Check status of all containers
docker ps

# Dynamically change the number of app instances (e.g. scale to 6 instances)
docker compose up -d --scale app=6

# Inspect cached keys in Redis
docker compose exec redis redis-cli keys "url:*"

# Stop all containers (preserves database volume)
docker compose down

# Stop all containers and wipe database/cache volume (destructive)
docker compose down -v
```

---

## Local Deployment (Development)

### Prerequisites

- **Python 3.13** (managed automatically via `uv`)
- **[uv](https://github.com/astral-sh/uv)** installed
- **PostgreSQL** running locally on port `5432`
- **Redis** running locally on port `6379`

### Steps

```bash
# 1. Clone the repo
git clone <repo-url>
cd mlh-production-engineering-hackathon-proj

# 2. Create the PostgreSQL database
createdb -U postgres hackathon_db

# 3. Configure environment
cp .env.example .env
# Ensure DATABASE_HOST=localhost and REDIS_HOST=localhost in .env

# 4. Install dependencies
uv sync

# 5. Start the development server
uv run python run.py
```

The application starts at **http://localhost:5000**.

Verify it is up:
```bash
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

---

## Deploying an Update

### Docker (Production Fleet)

```bash
# 1. Pull the latest code
git pull origin main

# 2. Rebuild and launch the updated fleet with scaled replicas
docker compose up -d --build --scale app=4
```

`--build` rebuilds the application image with any new code or dependencies. The database volume remains untouched and persistent.

### Local

```bash
git pull origin main
uv sync
uv run python run.py
```

---

## Rollback

### 1. Rolling Back Code

Find the target commit to revert to:

```bash
git log --oneline
```

**Option A — Safe Revert (Preserves history):**
```bash
git revert HEAD          # Undo the last commit
git push origin main     # Push the revert commit
```

**Option B — Hard Reset (Use with caution):**
```bash
git reset --hard <commit-hash>
git push --force origin main
```

### 2. Redeploying After a Rollback

```bash
# Rebuild containers from the rolled-back commit
docker compose up -d --build --scale app=4

# (Optional) If the rollback modified cache key structures, flush Redis:
docker compose exec redis redis-cli flushall
```

### 3. Database Considerations

The application schema is managed via Peewee ORM in `run.py` at startup via `db.create_tables([Url], safe=True)`.
- `safe=True` ensures `CREATE TABLE` is skipped if the table already exists.
- If a rollback removes a database column or model that existing rows depend on, manually inspect the database before restarting using `psql -U postgres hackathon_db`.

---

## Verifying a Deployment

Run through this checklist after every deployment or rollback:

```bash
# 1. Health endpoint responds
curl http://localhost:5000/health
# Expected: {"status": "ok"}

# 2. Metrics endpoint is collecting stats
curl http://localhost:5000/metrics
# Expected: JSON containing requests_total, latency_ms, and memory stats

# 3. Shorten a URL via API (populates DB and Redis cache)
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# Expected: HTTP 201 Created with short_code and short_url

# 4. Follow the short link (verifies Redis fast-path redirect)
curl -L http://localhost:5000/<short_code>
# Expected: 302 redirect to https://example.com

# 5. Verify in-memory cache key creation
docker compose exec redis redis-cli keys "url:*"
# Expected: lists the generated url:<short_code> key

# 6. (Optional) Run automated load verification
uv run locust -f locustfile.py --headless -u 100 -r 20 --run-time 30s --host http://localhost:5000
# Expected: 0.0% failure rate with response times < 100ms
```
