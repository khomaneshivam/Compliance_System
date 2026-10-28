# PlantProof

**Enterprise Regulatory Intelligence & Compliance Evidence Management for Manufacturing**

---

## 1. System Overview

**PlantProof** is an enterprise regulatory intelligence and compliance-evidence management platform engineered for manufacturing organizations operating under Indian industrial jurisdictions (such as Maharashtra, Gujarat, and Central statutes including MPCB, DISH/Labour, PESO, CPCB, and MoEFCC).

The platform bridges official government gazette circulars, facility operational master data, deterministic rule-based applicability, and AI-assisted document verification with strict human-in-the-loop review.

> [!IMPORTANT]
> **Scope & Deployment Notice:**
> PlantProof is architected and tested as a self-contained modular monolith for local development, local demonstration, and offline automated testing. **Production cloud deployment (e.g. AWS/GCP infrastructure, Kubernetes manifests, terraform, CDN provisioning, TLS cert issuance) is explicitly OUT OF SCOPE.**

---

## 2. Core Architectural & Regulatory Tenets

1. **"AI Proposes, Humans Dispose":**
   - Artificial intelligence must **never** silently alter compliance registers or issue blanket statements that an enterprise is "legally compliant".
   - AI extracts parameters from evidence certificates and summarizes gazette notifications into candidate obligations.
   - Every proposal carries traceable provenance, an explicit review state (`PROPOSED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`), and an immutable audit trail entry recording user sign-off.
2. **"No Raw Machine Artifacts in Customer-Facing Views":**
   - The user interface never renders raw JSON trees, unhandled stack traces, database dumps, or raw LLM prompts.
   - Machine outputs are translated into clean badges, human-readable labels, and side-by-side verification previews.
3. **Deterministic Applicability vs. Probabilistic AI:**
   - Formal statutory applicability is computed by a deterministic AST boolean engine evaluated against typed plant profile parameters.
   - Generative LLMs and OCR models feed data into this engine; they never decide statutory legal obligations autonomously.

---

## 3. Implementation Status: Implemented vs. Mocked vs. Future

| Capability Domain | Status | Technical Implementation Details |
| :--- | :---: | :--- |
| **Authentication & RBAC** | **IMPLEMENTED** | JWT bearer tokens (`HS256`), bcrypt password hashing, 5 distinct roles (`SUPER_ADMIN`, `ADMIN`, `PLANT_MANAGER`, `EHS_MANAGER`, `VIEWER`, `AUDITOR`), in-memory sliding-window rate limiting. |
| **Facility Profile & Onboarding** | **IMPLEMENTED** | Multi-tenant plant profile, 5-step onboarding wizard (`/setup-wizard`) with server-side validation, industrial sector classification (Red/Orange/Green), hazardous chemical and equipment tracking. |
| **Applicability Engine** | **IMPLEMENTED** | Deterministic Abstract Syntax Tree (AST) evaluator (`app/modules/applicability/engine.py`), monotonic rule versioning, requirement register generation. |
| **Document Evidence Vault** | **IMPLEMENTED** | Multipart file upload, canonical tenant path containment (`storage/vault/{tenant_id}/`), MIME magic byte validation, dual-pane document review workbench (`/documents`). |
| **Document OCR & Extraction** | **MOCKED / HEURISTIC** | Local heuristic regex parser adapter (`LocalDocumentParserProvider`) extracting standard Indian certificate fields (consent order numbers, validity dates, equipment tags). Gemini Vision / Document AI adapters exist as pluggable provider interfaces. |
| **Regulatory Change Ingestion** | **IMPLEMENTED / MOCKED** | 8-stage ingestion pipeline with human review state machine (`PROPOSED` $\to$ `APPROVED`). Official portal scraper adapter interface (`RegulatorySourceScraperProvider`) with local synthetic fixture feeds for MPCB, CPCB, and Central Gazette notifications. |
| **Compliance Task Tracking** | **IMPLEMENTED** | Task lifecycle management (`PENDING`, `IN_PROGRESS`, `UNDER_REVIEW`, `COMPLETED`), assignment, comments, attachments, and deadline calendar. |
| **Readiness Reporting** | **IMPLEMENTED** | Executive compliance dossier generator, HTML export with complete XSS escaping, compliance score calculation, and gap remediation summaries. |
| **Direct Government e-Filing** | **FUTURE / NON-GOAL** | Direct automated form submission to MPCB/PESO/CPCB government portals is deliberately non-goal to prevent legal liability. |
| **Automated Legal Advice** | **OUT OF SCOPE** | PlantProof provides compliance data intelligence; it does not replace licensed legal counsel. |

---

## 4. Prerequisites

Before installing PlantProof locally, ensure your machine satisfies:

- **Python:** 3.11+ (Tested and verified with **Python 3.13.5**)
- **Node.js:** v18+ (Tested and verified with **Node.js v22.16.0** and **npm 10.9.2**)
- **Database:** Local SQLite (built-in, zero-dependency) or PostgreSQL 16+
- **Operating System:** Windows 10/11 (PowerShell), Linux, or macOS

---

## 5. Local Installation & Setup

### 5.1 Clone & Environment Configuration

```powershell
# 1. Clone repository or navigate to project directory
cd "d:\Complaince System"

# 2. Copy the environment configuration template
Copy-Item .env.example .env
```

Open `.env` in your text editor. The default settings use a zero-dependency local SQLite database (`plantproof.db`), suitable for local development and testing:
```ini
ENVIRONMENT="development"
DEBUG=true
SECRET_KEY="demo-fake-secret-key-do-not-use-in-production-plantproof-auth"
DATABASE_URL="sqlite:///./plantproof.db"
STORAGE_DIR="./storage/vault"
LOG_LEVEL="INFO"
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://127.0.0.1:5173","http://127.0.0.1:3000"]
```

### 5.2 Backend Virtual Environment & Dependencies

```powershell
# 1. Create a Python virtual environment
python -m venv venv

# 2. Activate the virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
# source venv/bin/activate

# 3. Upgrade pip and install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 5.3 Database Migrations & Demo Data Seeding

PlantProof uses **Alembic** for schema migrations and dedicated CLI commands for master data, demo data, and notifications:

```powershell
# Run database schema migrations
python -m app.cli migrate

# Seed statutory master regulatory catalogs (MPCB, DISH, PESO)
python -m app.cli seed-master-data

# Seed synthetic demo personas and manufacturing facilities
python -m app.cli seed-demo-users

# Run multi-channel reminder scan across tasks, requirements, documents, and reviews
python -m app.cli run-reminders
```

*(Note: The FastAPI application also auto-seeds master catalogs on its initial startup if the database is empty).*

### 5.4 Frontend Dependencies

```powershell
# Navigate to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Return to root directory
cd ..
``` 

---

## 6. Running Local Processes

PlantProof runs as two decoupled local processes: the FastAPI backend and the Vite React frontend.

### 6.1 Start the Backend Process (Port 8000)

In your first terminal window:
```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Verify backend health:
- **Health Check Endpoint:** `http://localhost:8000/api/v1/health`
- **Interactive Swagger UI (OpenAPI):** `http://localhost:8000/docs`
- **ReDoc API Documentation:** `http://localhost:8000/redoc`

### 6.2 Start the Frontend Process (Port 5173)

In a second terminal window:
```powershell
cd frontend
npm run dev
```

The PlantProof Web Application is now available at:
- **Web App URL:** `http://localhost:5173`

---

## 7. Synthetic Demo Personas & Credentials

The seed loader provisions synthetic manufacturing data for **Acme Manufacturing Pvt. Ltd.** (MIDC Chakan Industrial Area, Pune, Maharashtra) and **Beta Pharma Ltd.** (Ankleshwar, Gujarat).

All demo personas share the password: `DemoPass123!`

| Persona Name | Email Address | Password | Role | Primary Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Rohit Sharma** | `rohit.sharma@acme-mfg.in` | `DemoPass123!` | `PLANT_MANAGER` | Facility profile updates, assessment execution, readiness review |
| **Priya Deshmukh** | `priya.deshmukh@acme-mfg.in` | `DemoPass123!` | `EHS_MANAGER` | Evidence upload, document approval, task remediation, reports |
| **Amit Jadhav** | `amit.jadhav@acme-mfg.in` | `DemoPass123!` | `ADMIN` | User invitation, tenant settings, facility provisioning |
| **Vikram Mehta** | `vikram.mehta@acme-mfg.in` | `DemoPass123!` | `VIEWER` | Read-only inspection of registers and dashboards |
| **Sneha Patil** | `sneha.patil@acme-mfg.in` | `DemoPass123!` | `AUDITOR` | Read-only inspection of evidence vault, audit trails, and reports |
| **Vikram Singh** | `vikram.singh@beta-pharma.in` | `DemoPass123!` | `PLANT_MANAGER` | Multi-tenant isolation testing (Beta Pharma facility) |

---

## 8. Running Automated Tests

PlantProof enforces automated test discipline across backend services and frontend components.

### 8.1 Backend Test Suite (Pytest)

Run all 142 backend tests across unit, integration, and security suites:
```powershell
.\venv\Scripts\pytest
```

To run a specific test suite:
```powershell
# Run security and hardening tests
.\venv\Scripts\pytest tests/integration/test_security_hardening.py -v

# Run deterministic applicability engine unit tests
.\venv\Scripts\pytest tests/unit/test_applicability_engine.py -v

# Run regulatory ingestion and error sanitization unit tests
.\venv\Scripts\pytest tests/unit/test_regulatory_ingestion.py -v

# Run extraction quality and AI boundary tests
.\venv\Scripts\pytest tests/evaluation/test_extraction_quality.py -v
```

### 8.2 Frontend Test Suite (Vitest)

Run all 14 component and router integration tests:
```powershell
cd frontend
npm test
```

To run frontend type checking and production bundle compilation:
```powershell
cd frontend
npm run build
```

---

## 9. Resetting the Local Database

If you wish to wipe local state and re-seed clean demonstration data:

```powershell
# 1. Stop the running uvicorn process (Ctrl+C)

# 2. Delete the SQLite database file
Remove-Item -Force .\plantproof.db

# 3. Clean local file vault uploads (optional)
Remove-Item -Recurse -Force .\storage\vault\*

# 4. Re-run migrations and seed data
alembic upgrade head
python -m app.cli seed-demo-data

# 5. Restart uvicorn
uvicorn app.main:app --reload --port 8000
```

---

## 10. Local Troubleshooting Guide

| Issue / Symptom | Probable Cause | Immediate Remediation |
| :--- | :--- | :--- |
| **`Port 8000 already in use`** | A lingering `uvicorn` or Python process is holding the socket. | Run `Get-Process python \| Stop-Process -Force` in PowerShell, then restart uvicorn. |
| **`Port 5173 already in use`** | Another Vite dev server is running. | Vite will automatically offer port 5174, or kill the node process with `Get-Process node \| Stop-Process -Force`. |
| **`HTTP 429 Too Many Requests`** | Sliding-window rate limiter triggered on login, upload, or reports. | Inspect the `Retry-After` header. Wait 15–60 seconds before retrying. |
| **`HTTP 403 Forbidden on document download`** | Canonical path containment rejected traversal token or cross-tenant IDOR. | Ensure the authenticated user belongs to the tenant owning the requested document ID. |
| **`database is locked` (SQLite)** | Concurrent transactions writing to SQLite simultaneously during tests. | SQLite locks the file during writes. Ensure tests use separate temporary databases (handled automatically by `conftest.py`). |
| **`CORS Request Blocked`** | Frontend running on non-whitelisted origin. | Verify `BACKEND_CORS_ORIGINS` in `.env` includes your frontend port (e.g. `http://localhost:5173`). |

For extensive diagnostic procedures, see [docs/TROUBLESHOOTING.md](file:///d:/Complaince%20System/docs/TROUBLESHOOTING.md).

---

## 11. Complete Documentation Index

All system architecture, security reviews, test strategies, and operational guides are documented in the `docs/` directory:

| Document | Description |
| :--- | :--- |
| **[System Flow & Skeleton](file:///d:/Complaince%20System/docs/SYSTEM_FLOW_AND_SKELETON.md)** | **Authoritative master flow doc**: Complete website skeleton, internal workflows, data governance, and AI agent setup. |
| **[Product Overview](file:///d:/Complaince%20System/docs/PRODUCT_OVERVIEW.md)** | Target enterprise customer, core operational workflows, scope, and explicit non-goals. |
| **[System Architecture](file:///d:/Complaince%20System/docs/ARCHITECTURE.md)** | C4 diagrams, 12 modular domains, data flow boundaries, and zero-dependency local contracts. |
| **[Master Data Model](file:///d:/Complaince%20System/docs/MASTER_DATA_MODEL.md)** | Mermaid ER diagram, entity glossary, global master data vs. tenant data, and versioning models. |
| **[Regulatory Data Governance](file:///d:/Complaince%20System/docs/REGULATORY_DATA_GOVERNANCE.md)** | Official portal inventory (EGAZETTE, MPCB, CPCB, DISH), refresh intervals, 8-stage ingestion pipeline. |
| **[AI Safety & Human Review](file:///d:/Complaince%20System/docs/AI_SAFETY_AND_REVIEW.md)** | Provider abstractions, PII redaction (Aadhaar masking), confidence bands, prompt injection defenses. |
| **[API Conventions & Catalog](file:///d:/Complaince%20System/docs/API_CONVENTIONS.md)** | Unified response envelopes, error structures, rate limiting rules, and a catalog of all 72 active endpoints. |
| **[Security Threat Model](file:///d:/Complaince%20System/docs/SECURITY_THREAT_MODEL.md)** | Data classification (Tiers 0–4), 8 architectural trust boundaries, STRIDE threat catalog, and mitigations. |
| **[Security Review Report](file:///d:/Complaince%20System/docs/SECURITY_REVIEW.md)** | White-box source audit, 8 remediated findings (SEC-01 to SEC-08), automated verification evidence, dependency audit. |
| **[Test Strategy](file:///d:/Complaince%20System/docs/TEST_STRATEGY.md)** | Testing pyramid, breakdown of all 97 backend tests and 11 frontend tests, WCAG AA accessibility. |
| **[Load Test Runbook](file:///d:/Complaince%20System/docs/LOAD_TEST_RUNBOOK.md)** | Local performance benchmarking, SLO targets, 4 concurrency scenarios, rate limit 429 threshold awareness. |
| **[User Guide](file:///d:/Complaince%20System/docs/USER_GUIDE.md)** | Non-technical operational guide: setup wizard, requirements register, evidence vault review, tasks, and reports. |
| **[Administrator Guide](file:///d:/Complaince%20System/docs/ADMIN_GUIDE.md)** | Regulatory source health, AST rule authoring, human approval, version supersession, user invitations, and audit logs. |
| **[Troubleshooting Guide](file:///d:/Complaince%20System/docs/TROUBLESHOOTING.md)** | Diagnostic checklist, port conflict resolution, database lock remediation, error code index. |
| **[Known Limitations](file:///d:/Complaince%20System/docs/KNOWN_LIMITATIONS.md)** | Accurate summary of current capabilities, mock adapters, local storage boundaries, and future roadmap. |
| **[Implementation Gap Audit](file:///d:/Complaince%20System/docs/IMPLEMENTATION_GAP_AUDIT.md)** | Comprehensive baseline code audit, verification of claims vs code, and prompt roadmap. |
| **[Implementation Handover](file:///d:/Complaince%20System/docs/IMPLEMENTATION_HANDOVER.md)** | Final operational verification, test pass matrix (142 backend, 14 frontend), and sign-off report. |

### Architecture Decision Records (ADRs)
- **[ADR 0001: Modular Monolith Architecture](file:///d:/Complaince%20System/docs/adr/0001-modular-monolith.md)**
- **[ADR 0002: Declarative AST Rule Representation & Temporal Versioning](file:///d:/Complaince%20System/docs/adr/0002-regulatory-rule-versioning.md)**
- **[ADR 0003: AI Proposals vs. Human Sign-Off Boundaries](file:///d:/Complaince%20System/docs/adr/0003-ai-human-review-boundary.md)**
- **[ADR 0004: In-Memory Sliding-Window Rate Limiting](file:///d:/Complaince%20System/docs/adr/0004-sliding-window-rate-limiting.md)**
- **[ADR 0005: File Vault Containment, Tenant Isolation, and Header Sanitization](file:///d:/Complaince%20System/docs/adr/0005-file-vault-containment-and-isolation.md)**
