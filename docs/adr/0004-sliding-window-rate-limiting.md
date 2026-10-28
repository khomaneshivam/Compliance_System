# ADR 0004: In-Memory Sliding-Window Rate Limiting for Sensitive Endpoints

## Status
**Accepted**

## Context
PlantProof is an enterprise compliance management application processing factory operational parameters, legal consent letters, inspection reports, and audit certificates. Certain REST API endpoints are intrinsically sensitive to excessive invocation:

1. **Authentication (`POST /api/v1/auth/login`):** Susceptible to credential stuffing, dictionary attacks, and password brute-forcing.
2. **Evidence Ingestion (`POST /api/v1/documents/upload`):** High computational cost (MIME validation, PDF OCR text extraction, layout parsing) and physical disk vault storage consumption.
3. **Audit Reporting (`POST /api/v1/reports`):** CPU-intensive compilation of facility readiness assessments, AST rule verification histories, and HTML/PDF rendering.

While production environments can deploy edge web application firewalls (WAFs) or API gateways (e.g. Cloudflare, AWS WAF, Nginx), the application requires deterministic, self-contained rate limiting that functions reliably in local execution environments, self-hosted deployments, and automated testing suites without external infrastructural dependencies (such as mandatory Redis clusters).

## Decision
We implement a zero-dependency, thread-safe **In-Memory Sliding-Window Rate Limiter** (`SlidingWindowRateLimiter` in `app/core/rate_limit.py`) integrated into FastAPI via endpoint route dependencies:

1. **Sliding-Window Algorithm:**
   - Instead of a fixed-window counter (which permits bursts of up to $2 \times \text{limit}$ across window boundaries), each request timestamp is recorded in a monotonic FIFO queue (`collections.deque`) keyed by client IP or tenant identifier.
   - Timestamps older than `window_seconds` (default: 60s) are pruned prior to evaluation.
   - If the queue length exceeds `max_requests`, the request is rejected immediately.
2. **Deterministic Response Contract:**
   - Rejections return HTTP status code `429 Too Many Requests`.
   - The response includes a standard `Retry-After: <seconds>` HTTP header indicating the remaining wait time until the oldest request timestamp in the window expires.
   - The response body adheres to the unified PlantProof error envelope (`AppErrorResponse`) with error code `RATE_LIMIT_EXCEEDED`.
3. **Endpoint Limit Policies:**
   - `POST /api/v1/auth/login`: 15 requests / minute per client IP.
   - `POST /api/v1/documents/upload`: 30 requests / minute per client IP.
   - `POST /api/v1/reports`: 15 requests / minute per client IP.
4. **Memory Management & Pruning:**
   - Stale IP keys are purged opportunistically during eviction passes to prevent unbounded in-memory dictionary growth over long server uptimes.

## Consequences

### Positive
- Zero external infrastructure required; functions out of the box with standard Python standard library constructs (`threading.Lock`, `collections.deque`).
- Eliminates credential stuffing and denial-of-service risks against high-cost endpoints.
- RFC-compliant `Retry-After` header gives clients and automated frontends deterministic backoff guidance.
- Fully verified under automated negative testing (`tests/integration/test_security_hardening.py`).

### Negative / Trade-offs
- Rate limit state is local to each application worker process. When scaled across multiple worker processes or containers, rate limiting is per-process rather than globally aggregated unless backed by a distributed store (e.g., Redis).
- Application restarts reset in-memory rate counters.
