# PlantProof Load Benchmark Report: BASELINE

**Execution Timestamp (UTC):** 2026-10-24T06:05:44.805820+00:00  
**Target Scenario:** `baseline`  
**Commit / Working Tree:** `63836fb`  
**Target Host:** `http://localhost:8000` (Local Test Stack)  
**Safety Validation:** Verified via `tests/load/safety_guard.py` (Local target confirmed)  

---

## 1. Reference Environment & Hardware Specifications

- **Operating System:** Windows 11 (AMD64)
- **Python Runtime:** CPython 3.13.5
- **Logical CPU Cores:** 12 cores
- **Total Physical Memory:** 7.65 GB RAM
- **Initial Host Resource Utilization:** CPU: 53.2%, Memory: 91.4%
- **Peak Host Resource Utilization:** CPU: 28.2%, Memory: 89.5%
- **Active Dataset Configuration:** Default seeded tenant personas (Acme Manufacturing & Beta Pharma)

---

## 2. Benchmark Scenario Parameters

- **Concurrent Users:** 25
- **Spawn Rate:** 5 users/second
- **Configured Duration:** 30s (Actual wall-clock: 32.44s)
- **Profile Objective:** Baseline Profile: 25 concurrent users simulating standard daily factory operations.

---

## 3. Measured Results vs. Configurable SLO Targets

> [!NOTE]
> The performance budgets listed below represent configured engineering **TARGETS** for local reference hardware rather than claimed production guarantees.

| Metric | Measured Value | Configured Target | Target Status |
| :--- | :---: | :---: | :---: |
| **Total Requests Completed** | **260** | >= 50 | PASS |
| **Average Throughput (Req/sec)** | **9.18 req/s** | N/A | Informational |
| **Median Latency (p50)** | **18.0 ms** | <= 400 ms | PASS |
| **Core Read APIs Max p95** | **2000.0 ms** | <= 800 ms | FAIL |
| **Core Read APIs Error Rate** | **0.0% (0 errs)** | <= 1.0% | PASS |
| **95th Percentile Latency (Aggregated)** | **3500.0 ms** | <= 800 ms | REVIEW |
| **99th Percentile Latency (Aggregated)** | **4000.0 ms** | <= 1200.0 ms | REVIEW |
| **Failure / Error Rate (Aggregated)** | **0.0% (0 errors)** | <= 1.0% | PASS |
| **Core Operational Verdict** | **TARGETS MISSED / REVIEW** | All core targets satisfied | REVIEW |


---

## 4. Endpoint Latency Breakdown

| Endpoint / Operation | Total Requests | Failures | Median (p50) | 95th Percentile (p95) |
| :--- | :---: | :---: | :---: | :---: |
| `Auth: Login (Auditor)` | 4 | 0 | 4000.0 ms | 4300.0 ms |
| `Auth: Login (EHS Manager)` | 7 | 0 | 3600.0 ms | 3700.0 ms |
| `Auth: Login (Plant Manager)` | 10 | 0 | 3500.0 ms | 4000.0 ms |
| `Documents: List Evidence Vault` | 26 | 0 | 16.0 ms | 480.0 ms |
| `Facilities: Get Plant Profile` | 23 | 0 | 13.0 ms | 120.0 ms |
| `Facilities: List Plants` | 10 | 0 | 270.0 ms | 380.0 ms |
| `Master Data: List Acts` | 12 | 0 | 10.0 ms | 140.0 ms |
| `Master Data: List Authorities` | 12 | 0 | 10.0 ms | 200.0 ms |
| `Master Data: Paginated Requirements` | 48 | 0 | 16.0 ms | 2000.0 ms |
| `Regulatory: List Changes Inbox` | 16 | 0 | 14.0 ms | 160.0 ms |
| `Reports: List Readiness Reports` | 16 | 0 | 20.0 ms | 490.0 ms |
| `Requirements: Get Plant Obligations` | 50 | 0 | 21.0 ms | 200.0 ms |
| `Tasks: List Remediation Items` | 26 | 0 | 17.0 ms | 140.0 ms |

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
D:\Complaince System\venv\Scripts\python.exe -m locust -f tests/load/locustfile.py --headless --host http://localhost:8000 --users 25 --spawn-rate 5 --run-time 30s --csv artifacts\test-reports\locust_baseline_20261024_060511 --only-summary
```
