# PlantProof Load Benchmark Report: SMOKE

**Execution Timestamp (UTC):** 2026-10-24T05:41:02.575318+00:00  
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
- **Initial Host Resource Utilization:** CPU: 22.5%, Memory: 91.1%
- **Peak Host Resource Utilization:** CPU: 31.2%, Memory: 91.5%
- **Active Dataset Configuration:** Synthetic Scaled Dataset: 3 tenants, 6 facilities, 3 users

---

## 2. Benchmark Scenario Parameters

- **Concurrent Users:** 5
- **Spawn Rate:** 2 users/second
- **Configured Duration:** 20s (Actual wall-clock: 22.6s)
- **Profile Objective:** Smoke Profile: Validates basic concurrency (5 users) and responsiveness.

---

## 3. Measured Results vs. Configurable SLO Targets

> [!NOTE]
> The performance budgets listed below represent configured engineering **TARGETS** for local reference hardware rather than claimed production guarantees.

| Metric | Measured Value | Configured Target | Target Status |
| :--- | :---: | :---: | :---: |
| **Total Requests Completed** | **43** | >= 50 | REVIEW |
| **Average Throughput (Req/sec)** | **2.38 req/s** | N/A | Informational |
| **Median Latency (p50)** | **11.0 ms** | <= 400 ms | PASS |
| **95th Percentile Latency (p95)** | **2500.0 ms** | <= 800 ms | FAIL |
| **99th Percentile Latency (p99)** | **2700.0 ms** | <= 1200.0 ms | REVIEW |
| **Failure / Error Rate** | **11.63% (5 errors)** | <= 1.0% | FAIL |
| **Overall Benchmark Verdict** | **TARGETS MISSED / REVIEW** | All targets satisfied | REVIEW |

---

## 4. Endpoint Latency Breakdown

| Endpoint / Operation | Total Requests | Failures | Median (p50) | 95th Percentile (p95) |
| :--- | :---: | :---: | :---: | :---: |
| `Auth: Login (Auditor)` | 1 | 0 | 2409.0 ms | 2400.0 ms |
| `Auth: Login (EHS Manager)` | 2 | 0 | 2700.0 ms | 2700.0 ms |
| `Auth: Login (Plant Manager)` | 2 | 0 | 2698.4 ms | 2700.0 ms |
| `Documents: List Evidence Vault` | 6 | 0 | 11.0 ms | 64.0 ms |
| `Facilities: Get Plant Profile` | 5 | 5 | 4.0 ms | 65.0 ms |
| `Facilities: List Plants` | 2 | 0 | 63.0 ms | 63.0 ms |
| `Master Data: List Acts` | 3 | 0 | 5.0 ms | 8.0 ms |
| `Master Data: List Authorities` | 3 | 0 | 8.8 ms | 9.0 ms |
| `Master Data: Paginated Requirements` | 5 | 0 | 7.0 ms | 22.0 ms |
| `Regulatory: List Changes Inbox` | 2 | 0 | 75.6 ms | 76.0 ms |
| `Reports: List Readiness Reports` | 2 | 0 | 60.0 ms | 60.0 ms |
| `Requirements: Get Plant Obligations` | 7 | 0 | 14.0 ms | 49.0 ms |
| `Tasks: List Remediation Items` | 3 | 0 | 15.0 ms | 47.0 ms |

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
D:\Complaince System\venv\Scripts\python.exe -m locust -f tests/load/locustfile.py --headless --host http://localhost:8000 --users 5 --spawn-rate 2 --run-time 20s --csv artifacts\test-reports\locust_smoke_20261024_054039 --only-summary
```
