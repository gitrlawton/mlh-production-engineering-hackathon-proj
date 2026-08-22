# Decision Log

Why we made the technical choices we did. Each entry records the decision, the alternatives we considered, and the reasoning.

---

## DL-01: Flask as the web framework

**Decision:** Use Flask 3.1.

**Alternatives considered:** FastAPI, Django.

**Reasoning:**

Flask is minimal by design. The application core focuses on high-speed routing, template rendering, and lightweight API endpoints — it does not require Django's heavy ORM, admin panel, auth system, or database migrations framework. FastAPI was considered for the JSON API, but the requirement to serve an integrated web UI and alerts dashboard makes Flask's Jinja2 template rendering a natural fit. Flask also has a low learning curve, ensuring rapid development and maintainability.

---

## DL-02: Peewee as the ORM

**Decision:** Use Peewee 3.17.

**Alternatives considered:** SQLAlchemy, raw psycopg2 SQL.

**Reasoning:**

Peewee is lightweight and its API maps cleanly onto simple CRUD operations. For an application with a focused data model and simple query types (INSERT, SELECT by short_code, DELETE for test teardown, COUNT for health checks), SQLAlchemy's unit-of-work session model and declarative setup introduced unnecessary overhead. Raw SQL was considered but rejected because Peewee's `Model.create()` and `Model.get()` read clearly and prevent SQL injection vulnerabilities automatically. Peewee also integrates cleanly with Flask's request lifecycle via its `DatabaseProxy` and connection hooks.

---

## DL-03: PostgreSQL as the database

**Decision:** Use PostgreSQL 16.

**Alternatives considered:** SQLite, MySQL/MariaDB.

**Reasoning:**

SQLite was the simplest option but was ruled out because it locks database writes sequentially, making it unsuitable for concurrent URL creation requests. PostgreSQL was chosen over MySQL because of its strong SQL standards compliance, battle-tested concurrency management, and first-class support across containerized environments. The `UNIQUE` constraint on `short_code` is enforced directly at the database engine level, preventing duplicate collisions during concurrent inserts.

---

## DL-04: Per-request database connections & caching offload

**Decision:** Use per-request connection management for PostgreSQL, offloading read volume to Redis.

**Alternatives considered:** External connection poolers (e.g. PgBouncer), SQLAlchemy connection pooling.

**Reasoning:**

For individual Flask workers, opening a connection per request via `@app.before_request` and `@app.teardown_appcontext` is simple and reliable. While per-request TCP handshakes can create overhead under heavy read traffic, we addressed this directly by placing an in-memory Redis cache in front of PostgreSQL (see **DL-11**). Because Redis serves >99% of redirect lookups in sub-milliseconds from RAM, database read contention is eliminated without requiring the operational complexity of a connection pooler like PgBouncer.

---

## DL-05: `secrets.token_urlsafe(6)` for short code generation

**Decision:** Generate short codes as 6-byte URL-safe base64 strings using Python's `secrets` module.

**Alternatives considered:** Sequential integer IDs (base62-encoded), MD5/SHA hash of the URL, UUID.

**Reasoning:**

Sequential IDs are predictable and allow users to enumerate the entire database by incrementing IDs. Hashing the URL creates deterministic codes (preventing different users from getting distinct short links for the same target URL). UUIDs are excessively long for short links. `secrets.token_urlsafe(6)` produces 8 characters of random URL-safe base64, providing over ~281 trillion unique code combinations — sufficient to make collisions negligible while keeping URLs short. The `secrets` module is cryptographically secure, unlike standard `random`.

---

## DL-06: uv as the package manager

**Decision:** Use `uv` instead of `pip` or `poetry`.

**Alternatives considered:** pip + venv, poetry.

**Reasoning:**

`uv` is significantly faster than pip at resolving, building, and installing dependencies, which accelerates Docker image builds and CI test workflows. It also manages Python toolchains and virtual environments automatically without requiring separate tools like `pyenv`. It natively adheres to standard `pyproject.toml` packaging specifications (PEP 517/518) and provides deterministic lockfile resolution via `uv.lock`.

---

## DL-07: Docker Compose for multi-service orchestration

**Decision:** Use Docker Compose to orchestrate the multi-container fleet (Nginx, App replicas, Redis, PostgreSQL, and Datadog).

**Alternatives considered:** Kubernetes, running all dependencies natively on the host machine.

**Reasoning:**

Kubernetes introduces excessive operational overhead for a dedicated service fleet. Running all dependencies natively on the host requires manual installation and configuration of PostgreSQL, Redis, and Nginx on every developer's machine. Docker Compose provides a reproducible, one-command setup (`docker compose up -d --build --scale app=4`) that functions identically across macOS, Linux, and Windows. Container health checks (`depends_on: condition: service_healthy`) guarantee that the application only starts once PostgreSQL and Redis are ready to accept traffic.

---

## DL-08: GitHub Actions for CI

**Decision:** Use GitHub Actions with a `postgres:16` service container.

**Alternatives considered:** CircleCI, local pre-commit hooks only.

**Reasoning:**

GitHub Actions integrates natively with the repository without requiring external account setups or webhook infrastructure. Running PostgreSQL as a service container in CI mirrors the production environment closely. Test gates with automated coverage reports (`--cov=app`) ensure code quality and prevent regressions on every push.

---

## DL-09: URL validation via `urllib.parse` rather than regex

**Decision:** Validate URLs using Python's built-in `urllib.parse.urlparse`, verifying `scheme` and `netloc`.

**Alternatives considered:** Hand-rolled regular expressions, third-party validator packages.

**Reasoning:**

Regex URL validation is notoriously prone to edge-case bugs and ReDoS (Regular Expression Denial of Service) security risks. `urlparse` is built into the Python standard library, requires no external dependencies, and handles IPv6 addresses, query strings, and internationalized domain names reliably. Validation rules enforce that URLs start with `http` or `https`, include a valid network location, and do not exceed 2048 characters.

---

## DL-10: Nginx for reverse proxy & horizontal load balancing

**Decision:** Place an Nginx container in front of scaled Flask application replicas using round-robin load balancing.

**Alternatives considered:** Traefik, HAProxy, single-container multithreading.

**Reasoning:**

Horizontal scaling is necessary to distribute concurrent load across multiple CPU cores. Placing Nginx at the ingress boundary allows the application to scale dynamically (`--scale app=N`) without host port collisions. Nginx leverages Docker's internal DNS resolution to discover all active container IPs under the `app` service and distributes incoming traffic evenly across them using round-robin balancing while offloading TCP connection keep-alives.

---

## DL-11: Redis for in-memory read-through and write-through caching

**Decision:** Use Redis (`redis:alpine`) for in-memory URL mapping (`url:<short_code>` ➔ `original_url`) with a 1-hour TTL and graceful database fallback.

**Alternatives considered:** In-process Python memory caches (`functools.lru_cache`), Memcached, database read replicas.

**Reasoning:**

In-process Python caches are local to a single worker process and cannot share cached data across multiple scaled container replicas. Memcached lacks rich key inspection tools and persistence options. Redis provides sub-millisecond lookups from RAM, enabling the system to sustain 240+ requests/sec under heavy concurrency with 0.0% failure rates. The integration is implemented with graceful degradation: if Redis is temporarily offline, requests fall back to PostgreSQL automatically without returning 500 errors to users.

---

## DL-12: Datadog APM & DogStatsD via Unix domain sockets

**Decision:** Use `ddtrace-run` and the official Datadog Agent container connected via shared `/var/run/datadog` Unix domain sockets.

**Alternatives considered:** OpenTelemetry + Jaeger, Prometheus + Grafana, manual application logging.

**Reasoning:**

`ddtrace-run` automatically instruments Flask endpoints, database queries, and Redis operations with zero invasive application code changes. Communicating with the Datadog Agent over Unix domain sockets (`apm.socket` and `dsd.socket`) eliminates network port overhead and reduces CPU utilization compared to TCP/UDP sockets.

---

## DL-13: In-app sliding window & Discord webhooks for incident alerting

**Decision:** Track HTTP 5xx error rates across a rolling 50-request sliding window in memory, dispatching diagnostic alerts to Discord with a 5-minute cooldown.

**Alternatives considered:** External uptime monitors (Pingdom, UptimeRobot), log-scraping cron jobs.

**Reasoning:**

Evaluating error rates in real-time within the application request pipeline (`app/alerts.py`) allows immediate anomaly detection without relying on polling intervals or external SaaS dependencies. The automated cooldown mechanism (`cooldown_seconds: 300` in `alerts.yml`) prevents webhook rate-limiting and channel spam during sustained incidents while ensuring operators receive actionable diagnostic payloads.
