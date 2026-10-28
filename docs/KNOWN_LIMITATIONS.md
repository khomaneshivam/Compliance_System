# PlantProof: Known Limitations & Architecture Decisions

**System Version:** v1.0.0  
**Status:** Current Implementation State  
**Scope:** Architecture Constraints, Operational Boundaries, and Technical Assumptions  

---

## 1. Geographic & Statutory Scope Limitations

### 1.1 Supported Jurisdictions & Catalog Depth
- **Initial Jurisdiction Focus:** The statutory requirements catalog and applicability rule sets included in the repository cover **Maharashtra State**, **Gujarat State**, and **Indian Central Statutes** (MPCB, GPCB, DISH Maharashtra, MoEFCC, Chief Inspector of Boilers, PESO, ESIC, CPCB).
- **Seed / Demo Labeling:** All pre-loaded catalog entries are explicitly designated as **SEED / BENCHMARK DATA**. They are designed for architecture validation and local integration testing, and must be reviewed by certified environmental and legal advocates before operational certification in live manufacturing plants.
- **Other State Jurisdictions:** Jurisdictions such as Tamil Nadu (TNPCB), Karnataka (KSPCB), Telangana (TSPCB), and Uttar Pradesh (UPPCB) are not yet populated in the default master data catalog.

---

## 2. Ingestion & Document Processing Boundaries

### 2.1 Live Government Scrapers vs. Offline Fixture Adapters
- **Explicit Mode Disclosure:** Every regulatory intelligence source and detected change explicitly labels its operational mode:
  - `FIXTURE` (`🧪 Test Fixture Feed`): Deterministic local benchmark fixtures (e.g. `fixture://regulatory-vault/demo-feed`) loaded from versioned test assets. Used for zero-dependency development, regression testing, and CI pipelines without external network volatility.
  - `LIVE_HTTP` (`🌐 Live Portal`): Active HTTP polling against official government gazette portals (e.g., eGazette, MPCB, CPCB). Strictly conforms to robots.txt, anti-SSRF protections, and a 1 request / 5s polite rate limit.
  - `DISABLED`: Inactive or paused regulatory feeds.
  - `FAILED`: Sources in degraded health status (`health_status == "UNAVAILABLE"` or $\ge 3$ consecutive polling failures).
- **No Access Control Bypasses:** PlantProof does **not** attempt to bypass logins, CAPTCHAs, Cloudflare WAF, or government anti-bot defenses.
- **Error Sanitization Policy (Cardinal UX Rule):**
  - Raw network tracebacks, internal database exception strings, and server file paths are strictly neutralized before returning to API consumers.
  - Ingestion errors are categorized into 8 standardized error categories: `PAYLOAD_OVERSIZED`, `MALFORMED_STREAM`, `SECURITY_BLOCKED`, `TIMEOUT`, `NETWORK_UNREACHABLE`, `SERVICE_THROTTLED`, `EXTRACTION_PARSE_ERROR`, and `INTERNAL_PROCESSING_ERROR`.
  - Every error is paired with actionable operational remediation instructions for compliance officers.

### 2.2 OCR & Document Extraction Modes
- **Extraction Provider Mode Disclosure:**
  - `FIXTURE` (`🧪 Synthetic Test Extractor`): Fast, deterministic heuristic/regex parser adapter calibrated for standard Indian statutory formats (Consent to Operate, Factory Licence, PESO Petroleum Licences, Hazardous Waste Authorizations). Provides 100% precision/recall on reference benchmarks without billable external API dependencies.
  - `LIVE_OCR` (`🌐 Live Vision OCR`): Google Cloud Document AI or Gemini Vision provider adapters for production deployments.
  - `FAILED`: Document extraction failure state with sanitized error categories and dual-pane human remediation.
- **Language Scope:** Default heuristic and vision extraction adapters are calibrated for English and bilingual English-Marathi / English-Hindi official forms.
- **Handwritten Annotations & Rubber Stamps:** Highly degraded historical scanned certificates with cursive handwritten officer notations or circular rubber stamps over text trigger low confidence scores ($< 0.600$), requiring manual human review.

---

## 3. Local Development & Infrastructure Architecture

### 3.1 Local Zero-Dependency Execution
- **Database Engine:** The primary production target is PostgreSQL 16+ using SQLAlchemy 2.0. For local developer workstations and isolated test execution, a zero-dependency SQLite dialect (`plantproof.db` / `sqlite:///:memory:`) is used by default.
- **Background Worker Processing:** Background job queues default to synchronous, in-process execution when Redis is disabled (`REDIS_ENABLED=false` in `.env`), ensuring full feature usability without external container dependencies.
- **In-Memory Rate Limiting Boundaries:**
  - Local rate limiting uses a thread-safe sliding window implementation (`app/core/rate_limit.py`).
  - *Operational Boundary:* In-memory sliding windows are scoped to a single Python process. In a horizontally scaled production deployment with multiple Uvicorn/Gunicorn worker processes behind a load balancer, rate limits must be backed by a distributed Redis token-bucket cluster.
- **Local Vault Storage:** Document and report storage defaults to the local filesystem (`./storage/vault/{tenant_id}/`). Cloud object storage adapters (AWS S3 / Google Cloud Storage) are defined via abstract provider interfaces for production infrastructure.

---

## 4. Explicit Scope Boundaries

| Capability | Current Baseline | Boundary & Scope Status |
| :--- | :--- | :--- |
| **Legal Certification** | Deterministic readiness scoring and evidence tracking. | **Out of Scope:** Does not provide formal legal opinions or absolute compliance guarantees ("AI Proposes, Humans Dispose"). |
| **Direct Portal Filing** | Scrapes public circulars and notifications. | **Out of Scope:** Does not execute bot form submissions or payment filings on government portals. |
| **Deployment Procedures** | Local development, multi-tenant isolation, automated test verification. | **Out of Scope:** Cloud deployment procedures, Kubernetes manifests, and production CI/CD pipelines are strictly out of scope for this repository. |
| **Distributed Rate Limiting** | Thread-safe in-memory sliding window limiter. | **Production Requirement:** Switch to Redis token-bucket when scaling beyond a single worker process. |
| **External Document AI** | Offline synthetic extractor adapter (`FIXTURE`). | **Production Requirement:** Configure Google Document AI or Cloud Vision credentials for live enterprise document vaults. |

---

## 5. Architectural Decision Backlog

1. **Digital Signature Integration:** Should PlantProof integrate with Indian Aadhaar eSign (e-Mudhra / NSDL) or Class 3 DSC (Digital Signature Certificate) hardware tokens for non-repudiation of executive reviews?
2. **External Notification Gateways:** Should SMS or WhatsApp Business API integrations be introduced for urgent statutory renewal alerts to factory supervisors?
3. **Multi-Region Cloud Federation:** Should enterprise customers with plants in multiple countries be supported via country-specific regulatory modules?
