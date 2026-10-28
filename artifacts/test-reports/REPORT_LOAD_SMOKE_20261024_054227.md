# PlantProof Load Benchmark Report: SMOKE

**Execution Timestamp (UTC):** 2026-10-24T05:43:00.233186+00:00  
**Target Scenario:** `smoke`  
**Commit / Working Tree:** `63836fb`  
**Target Host:** `http://localhost:8000` (Local Test Stack)  
**Safety Validation:** Verified via `tests/load/safety_guard.py` (Local target confirmed)  

---

## 1. Reference Environment & Hardware Specifications

- **Operating System:** Windows 11 (AMD64)
- **Python Runtime:** CPython 3.13.5
- **Logical CPU Cores:** 12 cores
- **Total Physical Memory:** 7.65 GB RAM
- **Initial Host Resource Utilization:** CPU: 21.5%, Memory: 92.6%
- **Peak Host Resource Utilization:** CPU: 14.5%, Memory: 91.2%
- **Active Dataset Configuration:** Default seeded tenant personas (Acme Manufacturing & Beta Pharma)

---

## 2. Benchmark Scenario Parameters

- **Concurrent Users:** 5
- **Spawn Rate:** 2 users/second
- **Configured Duration:** 30s (Actual wall-clock: 32.15s)
- **Profile Objective:** Smoke Profile: Validates basic concurrency (5 users) and responsiveness.

---

## 3. Measured Results vs. Configurable SLO Targets

> [!NOTE]
> The performance budgets listed below represent configured engineering **TARGETS** for local reference hardware rather than claimed production guarantees.

| Metric | Measured Value | Configured Target | Target Status |
| :--- | :---: | :---: | :---: |
| **Total Requests Completed** | **68** | >= 50 | PASS |
| **Average Throughput (Req/sec)** | **2.38 req/s** | N/A | Informational |
| **Median Latency (p50)** | **9.0 ms** | <= 400 ms | PASS |
| **95th Percentile Latency (p95)** | **2300.0 ms** | <= 800 ms | FAIL |
| **99th Percentile Latency (p99)** | **2400.0 ms** | <= 1200.0 ms | REVIEW |
| **Failure / Error Rate** | **1.47% (1 errors)** | <= 1.0% | FAIL |
| **Overall Benchmark Verdict** | **TARGETS MISSED / REVIEW** | All targets satisfied | REVIEW |

---

## 4. Endpoint Latency Breakdown

| Endpoint / Operation | Total Requests | Failures | Median (p50) | 95th Percentile (p95) |
| :--- | :---: | :---: | :---: | :---: |
| `Auth: Login (Auditor)` | 1 | 0 | 2331.8 ms | 2300.0 ms |
| `Auth: Login (EHS Manager)` | 2 | 0 | 2400.0 ms | 2400.0 ms |
| `Auth: Login (Plant Manager)` | 2 | 0 | 2388.0 ms | 2400.0 ms |
| `Documents: List Evidence Vault` | 9 | 0 | 8.0 ms | 18.0 ms |
| `Facilities: Get Plant Profile` | 5 | 0 | 10.0 ms | 19.0 ms |
| `Facilities: List Plants` | 2 | 0 | 18.0 ms | 18.0 ms |
| `Master Data: List Acts` | 6 | 0 | 6.0 ms | 2000.0 ms |
| `Master Data: List Authorities` | 6 | 1 | 7.0 ms | 9.0 ms |
| `Master Data: Paginated Requirements` | 13 | 0 | 8.0 ms | 17.0 ms |
| `Regulatory: List Changes Inbox` | 4 | 0 | 14.0 ms | 14.0 ms |
| `Reports: List Readiness Reports` | 1 | 0 | 10.8 ms | 11.0 ms |
| `Requirements: Get Plant Obligations` | 10 | 0 | 10.0 ms | 18.0 ms |
| `Tasks: List Remediation Items` | 7 | 0 | 10.0 ms | 15.0 ms |

---

## 5. Architectural Bottlenecks & Optimization Observations

1. **In-Memory Rate Limiting:**
   - The thread-safe sliding window rate limiter protects `/auth/login` (15 req/min) and heavy endpoints. During higher concurrency bursts, excess login attempts are throttled with HTTP 429 and RFC-compliant `Retry-After` headers.
2. **SQLite Database Locking Boundary:**
   - Under local SQLite execution, concurrent writes acquire an exclusive database lock. For multi-worker production throughput, PostgreSQL with a connection pool (`DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10`) is recommended.
3. **Faceted Pagination Indexing:**
   - Faceted queries on `/api/v1/master-data/requirements` benefit from indexed columns (`act_id`, `obligation_type`, `code`). Paginating with `page_size <= 100` prevents memory bloat.

---

## 6. Execution Command Line

```bash
D:\Complaince System\venv\Scripts\python.exe -m locust -f tests/load/locustfile.py --headless --host http://localhost:8000 --users 5 --spawn-rate 2 --run-time 30s --csv artifacts\test-reports\locust_smoke_20261024_054227 --only-summary
```
