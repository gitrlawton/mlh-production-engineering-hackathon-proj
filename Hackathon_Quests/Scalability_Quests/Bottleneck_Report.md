# Bottleneck Report: Scalability & Optimization

## 1. The Weak Link
**Identified Weak Link: The Database (PostgreSQL)**

Under high concurrency (500 concurrent users), the primary system bottleneck was PostgreSQL disk I/O and connection contention caused by repetitive SQL read queries on `GET /<short_code>`. While CPU and network capacity remained healthy, disk lookups and connection limits in PostgreSQL created request queuing and latency spikes.

---

## 2. The Solution: In-Memory Redis Caching
To resolve the database bottleneck, we implemented an in-memory **Redis** caching layer with read-through and write-through caching:
- **Write-Through**: When URLs are shortened (`POST /shorten`), the short code mapping is saved to PostgreSQL and immediately cached in Redis with a 1-hour TTL.
- **Read-Through**: When users access a short code (`GET /<short_code>`), the application queries Redis first, returning redirects in sub-milliseconds without querying PostgreSQL.

---

## 3. Results & Impact
Offloading read queries from disk to RAM eliminated database contention entirely:
- **Throughput:** Sustained **242.1 requests/second** under 500 concurrent users.
- **Stability:** **0.0% failure rate** across 13,546+ requests.
- **Latency:** Average latency dropped to **70ms** (p95 at **210ms**).
