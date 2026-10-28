"""
PlantProof Automated Load Test Runner & Reporting Engine
Executes Locust headless scenarios against local test stack and generates
structured benchmark reports in artifacts/test-reports/.
"""

import os
import sys
import time
import json
import subprocess
import platform
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psutil
from tests.load.safety_guard import validate_load_test_target, LoadTestSafetyViolation


SCENARIO_CONFIGS = {
    "smoke": {
        "users": 5,
        "spawn_rate": 2,
        "run_time": "30s",
        "description": "Smoke Profile: Validates basic concurrency (5 users) and responsiveness.",
        "target_p95_ms": 800,
        "target_error_rate_pct": 1.0,
    },
    "baseline": {
        "users": 25,
        "spawn_rate": 5,
        "run_time": "60s",
        "description": "Baseline Profile: 25 concurrent users simulating standard daily factory operations.",
        "target_p95_ms": 800,
        "target_error_rate_pct": 1.0,
    },
    "stress": {
        "users": 100,
        "spawn_rate": 10,
        "run_time": "60s",
        "description": "Stress Profile: 100 concurrent users testing throughput and resource limits.",
        "target_p95_ms": 1500,
        "target_error_rate_pct": 3.0,
    },
    "spike": {
        "users": 150,
        "spawn_rate": 50,
        "run_time": "45s",
        "description": "Spike Profile: Fast ramp to 150 users to evaluate queue surge and recovery.",
        "target_p95_ms": 2000,
        "target_error_rate_pct": 5.0,
    },
    "soak": {
        "users": 25,
        "spawn_rate": 5,
        "run_time": "300s",  # Configurable up to 1800s (30m)
        "description": "Soak Profile: Sustained concurrency to identify memory leaks or pool exhaustion.",
        "target_p95_ms": 1000,
        "target_error_rate_pct": 1.5,
    },
}


def get_git_commit_hash() -> str:
    """Retrieves current git commit hash if available, else 'local_build'."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except Exception:
        return "local_working_tree"


def run_scenario(
    scenario_name: str,
    target_url: str = "http://localhost:8000",
    custom_users: int = None,
    custom_time: str = None,
    seed_fixtures: bool = False,
) -> Path:
    """Executes a load test scenario and writes reports under artifacts/test-reports/."""
    # 1. Enforce safety validation
    validate_load_test_target(target_url)

    if scenario_name not in SCENARIO_CONFIGS:
        raise ValueError(f"Unknown scenario '{scenario_name}'. Permitted: {list(SCENARIO_CONFIGS.keys())}")

    cfg = SCENARIO_CONFIGS[scenario_name].copy()
    if custom_users:
        cfg["users"] = custom_users
    if custom_time:
        cfg["run_time"] = custom_time

    print(f"\n=======================================================")
    print(f" PlantProof Load Testing Benchmark - Scenario: {scenario_name.upper()}")
    print(f" Target URL: {target_url} (Verified Local Stack)")
    print(f" Users: {cfg['users']} | Spawn Rate: {cfg['spawn_rate']}/s | Duration: {cfg['run_time']}")
    print(f" Description: {cfg['description']}")
    print(f"=======================================================\n")

    # Seed synthetic load data if requested
    dataset_info = "Default seeded tenant personas (Acme Manufacturing & Beta Pharma)"
    if seed_fixtures:
        from app.core.database import SessionLocal
        from tests.load.synthetic_fixtures import generate_synthetic_load_dataset
        db = SessionLocal()
        try:
            summary = generate_synthetic_load_dataset(db, tenant_count=3, plants_per_tenant=2)
            dataset_info = f"Synthetic Scaled Dataset: {summary['tenants']} tenants, {summary['plants']} facilities, {summary['users']} users"
            print(f"[LOAD FIXTURES] {dataset_info}")
        finally:
            db.close()

    # Capture initial hardware metrics
    cpu_count = psutil.cpu_count(logical=True)
    mem_total_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    initial_cpu_pct = psutil.cpu_percent(interval=0.5)
    initial_mem_pct = psutil.virtual_memory().percent

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_dir = Path("artifacts/test-reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    csv_prefix = report_dir / f"locust_{scenario_name}_{timestamp_str}"

    locust_cmd = [
        sys.executable,
        "-m", "locust",
        "-f", "tests/load/locustfile.py",
        "--headless",
        "--host", target_url,
        "--users", str(cfg["users"]),
        "--spawn-rate", str(cfg["spawn_rate"]),
        "--run-time", cfg["run_time"],
        "--csv", str(csv_prefix),
        "--only-summary",
    ]

    print(f"Executing: {' '.join(locust_cmd)}\n")
    start_time = time.time()
    proc = subprocess.run(locust_cmd, capture_output=True, text=True)
    elapsed = round(time.time() - start_time, 2)

    # Capture final system metrics
    peak_cpu_pct = psutil.cpu_percent(interval=0.5)
    peak_mem_pct = psutil.virtual_memory().percent

    # Parse Locust CSV results
    stats_csv_path = Path(f"{csv_prefix}_stats.csv")
    parsed_stats = []
    total_reqs = 0
    total_failures = 0
    p50_ms = 0
    p95_ms = 0
    p99_ms = 0
    req_per_sec = 0.0

    if stats_csv_path.exists():
        import csv
        with open(stats_csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Name") == "Aggregated":
                    total_reqs = int(row.get("Request Count") or 0)
                    total_failures = int(row.get("Failure Count") or 0)
                    req_per_sec = float(row.get("Requests/s") or 0.0)
                    p50_ms = float(row.get("50%") or 0.0)
                    p95_ms = float(row.get("95%") or 0.0)
                    p99_ms = float(row.get("99%") or 0.0)
                else:
                    parsed_stats.append({
                        "name": row.get("Name"),
                        "method": row.get("Type"),
                        "requests": int(row.get("Request Count") or 0),
                        "failures": int(row.get("Failure Count") or 0),
                        "median_ms": float(row.get("Median Response Time") or 0.0),
                        "p95_ms": float(row.get("95%") or 0.0),
                    })

    actual_error_rate = round((total_failures / total_reqs * 100), 2) if total_reqs > 0 else 0.0

    # Core Read APIs isolation (evaluating operational performance target p95 < 800ms)
    core_read_stats = [st for st in parsed_stats if not st["name"].startswith("Auth:")]
    core_read_reqs = sum(st["requests"] for st in core_read_stats)
    core_read_failures = sum(st["failures"] for st in core_read_stats)
    core_read_error_rate = round((core_read_failures / core_read_reqs * 100), 2) if core_read_reqs > 0 else 0.0
    core_read_max_p95 = max((st["p95_ms"] for st in core_read_stats), default=0.0)
    core_read_avg_median = round(sum(st["median_ms"] * st["requests"] for st in core_read_stats) / core_read_reqs, 1) if core_read_reqs > 0 else 0.0

    # Evaluate against targets
    target_met_core_p95 = core_read_max_p95 <= cfg["target_p95_ms"]
    target_met_p95 = p95_ms <= cfg["target_p95_ms"]
    target_met_error = actual_error_rate <= cfg["target_error_rate_pct"]
    overall_target_status = "TARGETS MET" if (target_met_core_p95 and target_met_error) else "TARGETS MISSED / REVIEW"

    # Generate Markdown Report
    report_md_path = report_dir / f"REPORT_LOAD_{scenario_name.upper()}_{timestamp_str}.md"
    
    report_content = f"""# PlantProof Load Benchmark Report: {scenario_name.upper()}

**Execution Timestamp (UTC):** {datetime.now(timezone.utc).isoformat()}  
**Target Scenario:** `{scenario_name}`  
**Commit / Working Tree:** `{get_git_commit_hash()}`  
**Target Host:** `{target_url}` (Local Test Stack)  
**Safety Validation:** Verified via `tests/load/safety_guard.py` (Local target confirmed)  

---

## 1. Reference Environment & Hardware Specifications

- **Operating System:** {platform.system()} {platform.release()} ({platform.machine()})
- **Python Runtime:** {platform.python_implementation()} {platform.python_version()}
- **Logical CPU Cores:** {cpu_count} cores
- **Total Physical Memory:** {mem_total_gb} GB RAM
- **Initial Host Resource Utilization:** CPU: {initial_cpu_pct}%, Memory: {initial_mem_pct}%
- **Peak Host Resource Utilization:** CPU: {peak_cpu_pct}%, Memory: {peak_mem_pct}%
- **Active Dataset Configuration:** {dataset_info}

---

## 2. Benchmark Scenario Parameters

- **Concurrent Users:** {cfg['users']}
- **Spawn Rate:** {cfg['spawn_rate']} users/second
- **Configured Duration:** {cfg['run_time']} (Actual wall-clock: {elapsed}s)
- **Profile Objective:** {cfg['description']}

---

## 3. Measured Results vs. Configurable SLO Targets

> [!NOTE]
> The performance budgets listed below represent configured engineering **TARGETS** for local reference hardware rather than claimed production guarantees.

| Metric | Measured Value | Configured Target | Target Status |
| :--- | :---: | :---: | :---: |
| **Total Requests Completed** | **{total_reqs}** | >= 50 | {'PASS' if total_reqs >= 50 else 'REVIEW'} |
| **Average Throughput (Req/sec)** | **{req_per_sec:.2f} req/s** | N/A | Informational |
| **Median Latency (p50)** | **{p50_ms:.1f} ms** | <= 400 ms | {'PASS' if p50_ms <= 400 else 'REVIEW'} |
| **Core Read APIs Max p95** | **{core_read_max_p95:.1f} ms** | <= {cfg['target_p95_ms']} ms | {'PASS' if target_met_core_p95 else 'FAIL'} |
| **Core Read APIs Error Rate** | **{core_read_error_rate}% ({core_read_failures} errs)** | <= {cfg['target_error_rate_pct']}% | {'PASS' if core_read_error_rate <= cfg['target_error_rate_pct'] else 'FAIL'} |
| **95th Percentile Latency (Aggregated)** | **{p95_ms:.1f} ms** | <= {cfg['target_p95_ms']} ms | {'PASS' if target_met_p95 else 'REVIEW'} |
| **99th Percentile Latency (Aggregated)** | **{p99_ms:.1f} ms** | <= {cfg['target_p95_ms'] * 1.5} ms | {'PASS' if p99_ms <= cfg['target_p95_ms'] * 1.5 else 'REVIEW'} |
| **Failure / Error Rate (Aggregated)** | **{actual_error_rate}% ({total_failures} errors)** | <= {cfg['target_error_rate_pct']}% | {'PASS' if target_met_error else 'FAIL'} |
| **Core Operational Verdict** | **{overall_target_status}** | All core targets satisfied | {'PASS' if overall_target_status == 'TARGETS MET' else 'REVIEW'} |


---

## 4. Endpoint Latency Breakdown

| Endpoint / Operation | Total Requests | Failures | Median (p50) | 95th Percentile (p95) |
| :--- | :---: | :---: | :---: | :---: |
"""

    for st in parsed_stats:
        report_content += f"| `{st['name']}` | {st['requests']} | {st['failures']} | {st['median_ms']:.1f} ms | {st['p95_ms']:.1f} ms |\n"

    report_content += f"""
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
{' '.join(locust_cmd)}
```
"""

    report_md_path.write_text(report_content, encoding="utf-8")
    print(f"\n[BENCHMARK COMPLETE] Report written to: {report_md_path}")
    print(f"Results Summary: {total_reqs} requests, p50={p50_ms}ms, p95={p95_ms}ms, error_rate={actual_error_rate}%")
    return report_md_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PlantProof Load Testing Runner")
    parser.add_argument("--scenario", default="smoke", choices=list(SCENARIO_CONFIGS.keys()), help="Scenario profile")
    parser.add_argument("--target", default="http://localhost:8000", help="Target URL (must be local)")
    parser.add_argument("--users", type=int, default=None, help="Override concurrent users")
    parser.add_argument("--duration", type=str, default=None, help="Override duration (e.g. 30s, 1m)")
    parser.add_argument("--seed-fixtures", action="store_true", help="Seed scaled synthetic fixtures before test")

    args = parser.parse_args()
    try:
        run_scenario(
            scenario_name=args.scenario,
            target_url=args.target,
            custom_users=args.users,
            custom_time=args.duration,
            seed_fixtures=args.seed_fixtures,
        )
    except LoadTestSafetyViolation as err:
        print(f"\n[SAFETY ERROR] {err}", file=sys.stderr)
        sys.exit(1)
