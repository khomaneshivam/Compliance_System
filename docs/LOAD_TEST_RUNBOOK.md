# PlantProof: Performance Benchmarks & Load Testing Runbook

**System Version:** v1.0.0  
**Target Environment:** Local Workstation / Isolated Performance Test Bench  
**Test Frameworks:** Locust (Python-based load generator) / Async HTTP Benchmark Scripts  
**Status:** Grounded in Actual Application Architecture  

> [!CAUTION]
> **Safety & Authorization Notice:** Load tests must be executed strictly against local processes (`http://127.0.0.1:8000`) or designated performance test environments. Never target production systems, third-party government portals, or unauthorized external networks.

---

## 1. Performance Objectives & Service Level Objectives (SLOs)

PlantProof is engineered to support enterprise manufacturing operations tracking up to thousands of compliance obligations across multi-facility operations.

| User Workflow | Simulated Dataset Size | P50 Target | P95 Target | P99 Target | Concurrency Target | Max Error Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Dashboard KPI Summary** | 10 facilities per tenant | $< 50\text{ ms}$ | $< 150\text{ ms}$ | $< 300\text{ ms}$ | 50 concurrent users | $< 0.1\%$ |
| **Requirements Register Browse & Filter** | 500 requirements / plant | $< 80\text{ ms}$ | $< 250\text{ ms}$ | $< 500\text{ ms}$ | 50 concurrent users | $< 0.1\%$ |
| **Dry-Run Profile Simulation** | Full plant operational profile | $< 40\text{ ms}$ | $< 120\text{ ms}$ | $< 250\text{ ms}$ | 20 batch runs/sec | $< 0.0\%$ |
| **Evidence Document Upload & Parsing** | 5MB synthetic PDF certificate | $< 250\text{ ms}$| $< 600\text{ ms}$ | $< 1200\text{ ms}$| 10 uploads/sec | $< 0.1\%$ |
| **Readiness Report Generation (HTML)** | 50 requirements + gap analysis | $< 100\text{ ms}$| $< 350\text{ ms}$ | $< 750\text{ ms}$ | 10 jobs/sec | $< 0.1\%$ |

---

## 2. Benchmark Scenarios & User Profiles

### Scenario A: Operational Read Traffic (70% Weight)
- **User Actions:** Log in once, browse executive dashboard KPIs, filter requirements register by authority (`MPCB`, `DISH`) and status (`EXPIRING_SOON`, `MISSING`), paginate through results (pages 1 to 5).
- **Target Endpoints:**
  - `GET /api/v1/plants`
  - `GET /api/v1/requirements?plant_id={id}&page=1&page_size=10`
  - `GET /api/v1/reminders/notifications`

### Scenario B: Remediation Task Management (15% Weight)
- **User Actions:** Inspect task details, transition task status (`TODO` $\rightarrow$ `IN_PROGRESS`), post activity comments.
- **Target Endpoints:**
  - `GET /api/v1/tasks?plant_id={id}`
  - `POST /api/v1/tasks/{id}/status`
  - `POST /api/v1/tasks/{id}/comments`

### Scenario C: Evidence Upload & Review (10% Weight)
- **User Actions:** Upload synthetic PDF certificate, inspect extracted fields, approve document.
- **Target Endpoints:**
  - `POST /api/v1/documents/upload`
  - `GET /api/v1/documents/{id}`
  - `POST /api/v1/documents/{id}/review`
- **Rate Limit Note:** Upload load is configured to respect the 30 req/min/IP sliding window limit, or run with distributed client worker IPs.

### Scenario D: Reassessment Simulation & Reporting (5% Weight)
- **User Actions:** Simulate changes to boiler steam capacity or hazardous waste tonnage, generate executive HTML readiness dossier.
- **Target Endpoints:**
  - `POST /api/v1/companies/{id}/simulate-reassessment`
  - `POST /api/v1/reports?run_async=false`
  - `GET /api/v1/reports/{id}/download`

---

## 3. Local Execution Runbook

### Step 1: Pre-Populate Synthetic Benchmark Data
Ensure the database contains populated demo facilities and requirements:
```bash
# Verify database is seeded with Acme Manufacturing and Beta Pharma
.\venv\Scripts\python.exe -m app.seed.demo_data
```

### Step 2: Start Backend Application with Production Pool Tuning
Run the FastAPI application with multi-worker concurrency and PostgreSQL or optimized SQLite:
```bash
# In your project root:
.\venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --workers 2
```

### Step 3: Launch Local Synthetic Concurrency Script
You can execute synthetic concurrency testing using Locust or an asynchronous Python test harness:

```python
# Save as tests/load/local_benchmark.py
import asyncio
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"

async def test_worker(worker_id: int, num_requests: int):
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Authenticate
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "rohit.sharma@acme-mfg.in", "password": "DemoPass123!"}
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Fetch plants
        plants_resp = await client.get("/api/v1/plants", headers=headers)
        plant_id = plants_resp.json()[0]["id"]
        
        latencies = []
        for _ in range(num_requests):
            t0 = time.perf_counter()
            r = await client.get(f"/api/v1/requirements?plant_id={plant_id}&page=1&page_size=10", headers=headers)
            t1 = time.perf_counter()
            assert r.status_code == 200
            latencies.append((t1 - t0) * 1000)
            
        print(f"Worker {worker_id}: Avg={sum(latencies)/len(latencies):.2f}ms, Max={max(latencies):.2f}ms")

async def main():
    workers = 5
    reqs_per_worker = 20
    print(f"Starting local benchmark: {workers} workers x {reqs_per_worker} requests...")
    await asyncio.gather(*(test_worker(i, reqs_per_worker) for i in range(workers)))

if __name__ == "__main__":
    asyncio.run(main())
```

Execute the local benchmark:
```bash
.\venv\Scripts\python.exe tests/load/local_benchmark.py
```

---

## 4. Interpreting Results & Diagnosing Bottlenecks

### 4.1 Rate Limiting Triggers (HTTP 429)
- **Symptom:** Requests to `/api/v1/auth/login` or `/api/v1/documents/upload` return status code 429.
- **Cause:** Exceeding the in-memory sliding window rate limiter (15 login attempts/min or 30 uploads/min per IP).
- **Remediation:** In load tests, authenticate once per worker session and reuse the JWT token via Bearer headers for subsequent requests rather than logging in on every request.

### 4.2 Database Connection Pool Exhaustion
- **Symptom:** Requests hang and fail after 30 seconds with `TimeoutError: QueuePool limit of size 5 overflow 10 reached`.
- **Diagnosis:** Database sessions are held open during long operations, or concurrent requests exceed `DB_POOL_SIZE + DB_MAX_OVERFLOW`.
- **Remediation:** Increase `DB_POOL_SIZE=10` and `DB_MAX_OVERFLOW=20` in `.env`, and verify that all service endpoints close sessions via FastAPI's `Depends(get_db)` generator.

### 4.3 SQLite Concurrency Limitations
- **Symptom:** `sqlite3.OperationalError: database is locked`.
- **Cause:** SQLite uses file-level locking for writes. Multiple concurrent processes executing write operations simultaneously can block each other.
- **Remediation:** For high-concurrency write benchmarks, switch `.env` to PostgreSQL:
  ```env
  DATABASE_URL="postgresql+psycopg2://plantproof_user:password@localhost:5432/plantproof_dev"
  ```
