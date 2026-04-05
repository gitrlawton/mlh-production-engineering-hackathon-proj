# Decision Log

Why we made the technical choices we did. Each entry records the decision, the alternatives we considered, and the reasoning.

---

## DL-01: Flask as the web framework

**Decision:** Use Flask 3.1.

**Alternatives considered:** FastAPI, Django.

**Reasoning:**

Flask is minimal by design. This app has five routes and one model — it doesn't need Django's ORM, admin panel, auth system, or migrations framework. FastAPI would have been a reasonable choice for the JSON API, but the requirement to serve an HTML form as well makes Flask's template rendering support a natural fit. Flask also has the lowest learning curve for contributors unfamiliar with async Python, which matters for a hackathon context where onboarding speed is a priority.

---

## DL-02: Peewee as the ORM

**Decision:** Use Peewee 3.17.

**Alternatives considered:** SQLAlchemy, raw psycopg2 SQL.

**Reasoning:**

Peewee is lightweight and its API maps cleanly onto simple CRUD operations. For an app with one model and four query types (INSERT, SELECT by short_code, DELETE for test teardown, COUNT for health), SQLAlchemy's session/unit-of-work model and declarative setup would have been significant overhead. Raw SQL was considered but rejected because Peewee's `Model.create()` and `Model.get()` read clearly and reduce the risk of SQL injection with no extra effort. Peewee also integrates naturally with Flask's per-request lifecycle via its `DatabaseProxy` and `connect()`/`close()` hooks.

---

## DL-03: PostgreSQL as the database

**Decision:** Use PostgreSQL 16.

**Alternatives considered:** SQLite, MySQL/MariaDB.

**Reasoning:**

SQLite was the simplest option but ruled out because it doesn't support concurrent writes well — a URL shortener under any real load will have simultaneous POST requests. PostgreSQL was chosen over MySQL because it is the most widely supported production database in the Python/Flask ecosystem, has better compliance with SQL standards, and is what the MLH hackathon CI environment provides natively. The `UNIQUE` constraint on `short_code` is enforced at the database level, not just in application code, which prevents duplicates even under concurrent inserts.

---

## DL-04: Per-request database connections (no connection pool)

**Decision:** Open one connection per HTTP request; close it on teardown via `@app.teardown_appcontext`.

**Alternatives considered:** A persistent connection pool (e.g., PgBouncer, SQLAlchemy connection pool).

**Reasoning:**

For a single-process Flask development server with low concurrency, a connection pool adds complexity without benefit. Peewee's `DatabaseProxy` and `reuse_if_open=True` make the per-request pattern easy to implement correctly. The tradeoff is that each request pays the cost of a TCP handshake to Postgres; at scale this would be the first thing to change (see [CAPACITY_PLAN.md](CAPACITY_PLAN.md)), but for the scope of this project the simplicity is worth it.

---

## DL-05: `secrets.token_urlsafe(6)` for short code generation

**Decision:** Generate short codes as 6-byte URL-safe base64 strings using Python's `secrets` module.

**Alternatives considered:** Sequential integer IDs (base62-encoded), MD5/SHA hash of the URL, UUID.

**Reasoning:**

Sequential IDs are predictable — someone can enumerate all shortened URLs by incrementing the code. Hashing the URL creates a fixed code per URL (no duplicates for the same long URL), but it also means the same long URL always produces the same short code, which is a design choice we didn't need to commit to. UUIDs are too long for a short URL. `secrets.token_urlsafe(6)` produces 8 characters of random URL-safe base64, which gives ~281 trillion possible codes — sufficient to make collisions negligible. The `secrets` module is cryptographically random, unlike `random`, which matters if short codes are ever used as access tokens.

---

## DL-06: uv as the package manager

**Decision:** Use `uv` instead of `pip` or `poetry`.

**Alternatives considered:** pip + venv, poetry.

**Reasoning:**

`uv` is significantly faster than pip at resolving and installing dependencies, which matters in CI where a fresh install runs on every push. It also manages Python versions automatically (no separate `pyenv` needed), which simplifies onboarding on different machines. `pyproject.toml` is the standard packaging metadata format (PEP 517/518), and `uv` supports it natively. Poetry was considered but its lockfile format is non-standard; `uv` uses `uv.lock` and falls back gracefully to `pyproject.toml`.

---

## DL-07: Docker Compose for containerisation

**Decision:** Use Docker Compose to orchestrate the app and database containers.

**Alternatives considered:** Kubernetes, running Postgres directly on the host, Docker without Compose.

**Reasoning:**

Kubernetes is the right answer at scale but is far too much operational overhead for a two-service project. Running Postgres on the host works for development but requires contributors to install and configure PostgreSQL themselves. Docker Compose gives us a one-command setup (`docker compose up -d`) that works identically on any machine with Docker installed, and the `depends_on: condition: service_healthy` block ensures the app never starts before Postgres is ready — eliminating the most common source of startup failures.

---

## DL-08: GitHub Actions for CI

**Decision:** Use GitHub Actions with a `postgres:16` service container.

**Alternatives considered:** CircleCI, local pre-commit hooks only.

**Reasoning:**

GitHub Actions is free for public repositories and requires no external account setup. Running Postgres as a service container in CI mirrors the production Docker environment more closely than mocking the database. Pre-commit hooks alone don't catch integration failures across contributors' different environments. The `--cov-fail-under=50` coverage gate ensures tests aren't skipped silently as the codebase grows.

---

## DL-09: URL validation via `urllib.parse` rather than regex

**Decision:** Validate URLs using Python's built-in `urllib.parse.urlparse` and checking `scheme` and `netloc`.

**Alternatives considered:** A regex-based validator, a third-party library (e.g., `validators`).

**Reasoning:**

Regex URL validation is notoriously difficult to get right and easy to bypass. `urlparse` is part of the standard library, has no dependencies, and handles the edge cases (IPv6 addresses, IDN hostnames, unusual but valid schemes) that a hand-rolled regex would likely miss. The validation rules are intentionally minimal: require `http` or `https`, require a network location, cap at 2048 characters. Adding a third-party library for this one function would be premature — the standard library handles the requirement.
