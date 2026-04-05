# Deploy Guide

How to get the URL Shortener running, and how to roll back if something goes wrong.

---

## Deployment Options

There are two supported ways to run this app:

| Option | When to use |
|--------|-------------|
| [Local (no Docker)](#local-deployment) | Development, quick testing |
| [Docker Compose](#docker-deployment) | Preferred for any shared or production-like environment |

---

## Local Deployment

### Prerequisites

- Python 3.13
- [uv](https://github.com/astral-sh/uv) installed
- PostgreSQL running locally

### Steps

```bash
# 1. Clone the repo
git clone <repo-url>
cd mlh-production-engineering-hackathon-proj

# 2. Create the database
createdb -U postgres hackathon_db

# 3. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_PASSWORD to your Postgres password

# 4. Install dependencies
uv sync

# 5. Start the server
uv run run.py
```

The app starts at **http://localhost:5000**.

Verify it's up:

```bash
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

`run.py` creates the `url` table automatically on startup if it doesn't already exist.

---

## Docker Deployment

Docker Compose starts both the app and a PostgreSQL container — no local Postgres install needed.

### Steps

```bash
# 1. Clone the repo
git clone <repo-url>
cd mlh-production-engineering-hackathon-proj

# 2. Start everything
docker compose up -d

# 3. Verify
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

The `app` container waits for the `db` container to pass its health check before starting, so the database is always ready when the app comes up.

### Useful Docker commands

```bash
# View live logs
docker compose logs -f app

# Stop everything (preserves the database volume)
docker compose down

# Stop and wipe the database volume (destructive — all data is lost)
docker compose down -v

# Rebuild the app image after a code change
docker compose up -d --build
```

---

## Deploying an Update

### Local

```bash
git pull origin main
uv sync          # install any new dependencies
uv run run.py
```

### Docker

```bash
git pull origin main
docker compose up -d --build
```

`--build` rebuilds the `app` image from the updated code. The `db` container and its data volume are untouched.

---

## Rollback

### Rolling back the code

Every commit is a potential rollback target. Find the commit you want to return to:

```bash
git log --oneline
```

**Option A — revert (safe, keeps history):**

```bash
git revert HEAD          # undo the last commit
git push origin main     # push the revert commit
```

**Option B — reset (rewrites history, use with caution):**

```bash
git reset --hard <commit-hash>
git push --force origin main
```

### Redeploying after a rollback

**Local:**

```bash
uv sync
uv run run.py
```

**Docker:**

```bash
docker compose up -d --build
```

### Database considerations

This app's schema is minimal (one table: `url`). Schema changes are applied automatically by `run.py` at startup via `db.create_tables([Url], safe=True)`.

- `safe=True` means the `CREATE TABLE` is skipped if the table already exists — it will never drop data on a normal restart.
- If a rollback removes a column or table that existing rows depend on, manually inspect the database before restarting. Connect with `psql -U postgres hackathon_db` and verify.

---

## Verifying a Deployment

Run through this checklist after any deploy or rollback:

```bash
# 1. Health endpoint responds
curl http://localhost:5000/health
# Expected: {"status": "ok"}

# 2. Shorten a URL
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# Expected: HTTP 201, body contains short_code and short_url

# 3. Follow the short link
curl -L http://localhost:5000/<short_code>
# Expected: redirects to https://example.com
```

All three passing means the app, database connection, and redirect flow are working end to end.
