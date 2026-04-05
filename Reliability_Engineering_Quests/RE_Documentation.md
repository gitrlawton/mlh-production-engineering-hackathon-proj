# Reliability Engineering Documentation

---

## Error Handling

This section documents how the URL shortener handles error conditions, including what response is returned and under what circumstances.

### 400 Bad Request

**Route:** `POST /shorten`

**Cause:** The request body is missing the `url` field.

**Response:**

```json
{ "error": "url is required" }
```

**When it occurs:** The client sends a POST request to `/shorten` without a `url` key in the JSON body.

---

### 404 Not Found

**Route:** `GET /<short_code>`

**Cause:** The provided short code does not exist in the database.

**Response:**

```json
{ "error": "short code not found" }
```

**When it occurs:** A user visits a short URL (e.g. `/abc123`) but no record with that short code exists in the database — either it was never created, or the wrong code was entered.

---

### 500 Internal Server Error

**Cause:** Any unhandled exception in the application — for example, an unexpected database error or a bug in application code.

**Response:** Flask's default HTML error page. The app does not currently have a custom 500 handler, so the response is not JSON and exposes Flask's generic error template.

**Current gap:** API consumers (e.g. clients calling `POST /shorten`) would receive an HTML response on a 500, which is inconsistent with the JSON responses returned by all other routes. Implementing a custom JSON 500 handler is a Tier 3 objective.

---

## Failure Modes

This section documents specific failure scenarios — what causes them, what the app does, and what the user or operator sees.

Custom JSON error handlers are registered in `app/__init__.py` for both 404 and 500, ensuring all error responses are consistent JSON regardless of the failure type.

| Failure                                | Cause                                                      | App behaviour                                                        | User sees                                                        |
| -------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Database connection lost mid-request   | PostgreSQL goes down while the app is running              | Unhandled exception → 500 handler fires                              | `{"error": "internal server error"}`                             |
| Duplicate short code collision         | `secrets.token_urlsafe` generates a code already in the DB | `IntegrityError` (unique constraint violated) → 500 handler fires    | `{"error": "internal server error"}`                             |
| Malformed JSON body on `POST /shorten` | Client sends invalid or missing JSON                       | Flask raises `BadRequest` → route returns 400                        | `{"error": "url is required"}`                                   |
| App process killed                     | Container forcefully terminated (e.g. `docker kill`)       | Docker `restart: always` policy restarts the container automatically | Brief downtime, then service resumes without manual intervention |
| Unregistered route accessed            | Client hits a route that doesn't exist in the app          | Custom 404 handler fires                                             | `{"error": "not found"}`                                         |
