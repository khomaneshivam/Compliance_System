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

### 2.1 Live Government Scrapers vs. Offline Adapters
- **No Access Control Bypasses:** PlantProof does **not** bypass logins, CAPTCHAs, or anti-bot defenses on government compliance portals. Live web scraping of government portals respects `robots.txt` and is rate-limited to 1 req/5s per domain.
- **Offline / Local Fixture Execution:** To ensure zero-dependency local test execution without network failures, a local fixture adapter (`fixture://regulatory-vault/demo-feed`) is provided and used in integration tests.

### 2.2 OCR & Regional Language Limits
- **Language Scope:** Default heuristic and vision extraction adapters are calibrated for English and bilingual English-Marathi / English-Hindi official forms.
- **Handwritten Annotations & Rubber Stamps:** Highly degraded historical scanned certificates with cursive handwritten officer notations or circular rubber stamps over text trigger low confidence scores ($< 0.600$), requiring manual human review.

---

## 3. Local Development & Infrastructure Architecture

### 3.1 Local Zero-Dependency Execution
- **Database Engine:** The primary production target is PostgreSQL 16+ using SQLAlchemy 2.0. For local developer workstations and isolated test execution, a zero-dependency SQLite dialect (`plantproof.db` / `sqlite:///:memory:`) is used by default.
- **Background Worker Processing:** Background job queues default to synchronous, in-process execution when Redis is disabled (`REDIS_ENABLED=false` in `.env`), ensuring full feature usability without external container dependencies.
- **In-Memory Rate Limiting:** Rate limiting uses a thread-safe sliding window implementation (`app/core/rate_limit.py`). While optimal for single-process local servers, multi-instance horizontal scaling in production requires a distributed Redis token bucket limiter.
- **Local Vault Storage:** Document and report storage defaults to the local filesystem (`./storage/vault/{tenant_id}/`). Cloud object storage adapters (AWS S3 / Google Cloud Storage) are defined via abstract provider interfaces for production infrastructure.

---

## 4. Explicit Scope Boundaries

| Capability | Current Baseline | Boundary & Scope Status |
| :--- | :--- | :--- |
| **Legal Certification** | Deterministic readiness scoring and evidence tracking. | **Out of Scope:** Does not provide formal legal opinions or absolute compliance guarantees. |
| **Direct Portal Filing** | Scrapes public circulars and notifications. | **Out of Scope:** Does not execute bot form submissions or payment filings on government portals. |
| **Deployment Procedures** | Local development, multi-tenant isolation, automated test verification. | **Out of Scope:** Cloud deployment procedures, Kubernetes manifests, and production CI/CD pipelines are strictly out of scope for this repository. |

---

## 5. Architectural Decision Backlog

1. **Digital Signature Integration:** Should PlantProof integrate with Indian Aadhaar eSign (e-Mudhra / NSDL) or Class 3 DSC (Digital Signature Certificate) hardware tokens for non-repudiation of executive reviews?
2. **External Notification Gateways:** Should SMS or WhatsApp Business API integrations be introduced for urgent statutory renewal alerts to factory supervisors?
3. **Multi-Region Cloud Federation:** Should enterprise customers with plants in multiple countries be supported via country-specific regulatory modules?
