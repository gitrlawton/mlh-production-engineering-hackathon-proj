# URL Shortener — Project README

A URL shortening service built with Flask, Peewee ORM, and PostgreSQL.
Paste in a long URL, get a short link back. Click the short link, get redirected.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Client                           │
│              (Browser or HTTP client)                   │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP requests
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Flask App  (:5000)                   │
│                                                         │
│  ┌──────────────┐   ┌───────────────────────────────┐  │
│  │   Web UI     │   │         JSON API              │  │
│  │  GET  /      │   │  POST /shorten                │  │
│  │  POST /      │   │  GET  /health                 │  │
│  └──────────────┘   └───────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Redirect Handler                    │   │
│  │              GET /<short_code>                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │          Peewee ORM  (database.py)               │   │
│  │    Per-request connection open/close lifecycle   │   │
│  └────────────────────┬────────────────────────────┘   │
└───────────────────────┼─────────────────────────────────┘
                        │  SQL queries (psycopg2)
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  PostgreSQL  (:5432)                    │
│                                                         │
│   table: url                                            │
│   ┌────┬───────────────────────┬──────────────┐        │
│   │ id │     original_url      │  short_code  │        │
│   ├────┼───────────────────────┼──────────────┤        │
│   │  1 │ https://example.com/… │   aB3xYz     │        │
│   └────┴───────────────────────┴──────────────┘        │
└─────────────────────────────────────────────────────────┘
```

**Request flow:**

1. Client sends a URL to `POST /shorten`
2. Flask validates the URL (must be `http://` or `https://`, ≤ 2048 chars)
3. A random 8-character short code is generated using `secrets.token_urlsafe`
4. The mapping is stored in PostgreSQL via Peewee ORM
5. The short URL is returned to the client
6. When a client hits `GET /<short_code>`, Flask looks up the code and issues a `302` redirect

---

## Prerequisites

| Requirement | Version | Notes                         |
| ----------- | ------- | ----------------------------- |
| Python      | 3.13    | Managed automatically by `uv` |
| uv          | latest  | Fast Python package manager   |
| PostgreSQL  | 18+     | Local install or Docker       |

**Install uv:**

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Setup (Local — PostgreSQL on your machine)

```bash
# 1. Clone the repository
git clone <repo-url>
cd mlh-production-engineering-hackathon-proj

# 2. Create the database
createdb -U postgres hackathon_db

# 3. Copy and configure environment variables
cp .env.example .env
# Open .env and set DATABASE_PASSWORD if your Postgres user has one

# 4. Install all dependencies
uv sync

# 5. Start the server
uv run run.py
```

The app is now running at **http://localhost:5000**.

**Verify it's working:**

```bash
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

---

## Setup (Docker — no local PostgreSQL needed)

```bash
# Start both the app and the database
docker compose up -d

# Check the app is healthy
curl http://localhost:5000/health

# Stop everything
docker compose down
```

Docker handles the database automatically — no manual `createdb` needed.

---

## Environment Variables

All variables live in `.env` (copy from `.env.example`):

| Variable            | Default         | Description              |
| ------------------- | --------------- | ------------------------ |
| `DATABASE_NAME`     | `hackathon_db`  | PostgreSQL database name |
| `DATABASE_HOST`     | `localhost`     | PostgreSQL host          |
| `DATABASE_PORT`     | `5432`          | PostgreSQL port          |
| `DATABASE_USER`     | `postgres`      | PostgreSQL user          |
| `DATABASE_PASSWORD` | <your-password> | PostgreSQL password      |
| `FLASK_DEBUG`       | `false`         | Enable Flask debug mode  |

---

## Project Structure

```
mlh-production-engineering-hackathon-proj/
├── app/
│   ├── __init__.py          # App factory (create_app), health endpoint, error handlers
│   ├── database.py          # DatabaseProxy, BaseModel, per-request connection lifecycle
│   ├── models/
│   │   ├── __init__.py      # Model imports
│   │   └── url.py           # Url model (original_url, short_code)
│   ├── routes/
│   │   ├── __init__.py      # register_routes()
│   │   └── urls.py          # All URL shortener routes + validation logic
│   └── templates/
│       └── index.html       # Web UI (HTML form + result display)
├── tests/
│   ├── test_urls.py         # Route-level functional tests
│   ├── test_integration.py  # Database state integration tests
│   └── test_bonus.py        # Reliability edge-case tests
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI (runs tests on every push)
├── docker-compose.yml       # PostgreSQL + Flask containers
├── Dockerfile               # Flask app image
├── pyproject.toml           # Dependencies and project metadata
├── .env.example             # Environment variable template
├── run.py                   # Entry point: uv run run.py
└── README.md                # Template-level setup guide
```

---

## API Reference

### `GET /health`

Health check. Verifies the app is running and can reach the database.

**Response — healthy:**

```
HTTP 200 OK
{"status": "ok"}
```

**Response — database unreachable:**

```
HTTP 503 Service Unavailable
{"status": "unavailable", "reason": "database unreachable"}
```

---

### `GET /`

Serves the web UI — an HTML form where users can paste a URL and shorten it in the browser.

**Response:**

```
HTTP 200 OK
Content-Type: text/html
```

---

### `POST /`

Form-based URL shortening (used by the web UI). Accepts `application/x-www-form-urlencoded`.

**Request body (form field):**

| Field | Required | Description        |
| ----- | -------- | ------------------ |
| `url` | Yes      | The URL to shorten |

**Response — success:**

```
HTTP 200 OK
Content-Type: text/html
(renders page with the short URL displayed as a clickable link)
```

**Response — invalid URL:**

```
HTTP 200 OK
Content-Type: text/html
(renders page with error: "A valid URL is required (must start with http:// or https://)")
```

---

### `POST /shorten`

JSON API for programmatic URL shortening.

**Request:**

```
POST /shorten
Content-Type: application/json

{"url": "https://www.example.com/some/very/long/path"}
```

**Response — success:**

```
HTTP 201 Created
{
  "short_code": "aB3xYz12",
  "short_url": "http://localhost:5000/aB3xYz12"
}
```

**Response — missing or invalid URL:**

```
HTTP 400 Bad Request
{"error": "a valid url is required (must start with http:// or https://)"}
```

**Response — short code generation failed:**

```
HTTP 500 Internal Server Error
{"error": "could not generate a unique short code"}
```

---

### `GET /<short_code>`

Redirects the client to the original URL stored for the given short code.

**Example:** `GET /aB3xYz12`

**Response — found:**

```
HTTP 302 Found
Location: https://www.example.com/some/very/long/path
```

**Response — not found:**

```
HTTP 404 Not Found
{"error": "short code not found"}
```

---

## URL Validation Rules

The app accepts a URL only if **all** of the following are true:

- Scheme is `http` or `https` (rejects `ftp://`, `file://`, bare hostnames, etc.)
- A network location (domain or IP) is present
- Total length is 2048 characters or fewer
- Leading/trailing whitespace is stripped before validation

---

## Running Tests

```bash
# Run all tests with coverage report
uv run pytest tests/ -v --cov=app --cov-report=term-missing

# Run a specific test file
uv run pytest tests/test_urls.py -v

# Run tests and fail if coverage drops below 50%
uv run pytest tests/ --cov=app --cov-fail-under=50
```

Tests require a running PostgreSQL instance configured via `.env`.

---

## Quick Reference

```bash
# Shorten a URL (API)
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.example.com"}'

# Follow the short link
curl -L http://localhost:5000/<short_code>

# Check service health
curl http://localhost:5000/health
```
