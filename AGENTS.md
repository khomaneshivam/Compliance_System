# AGENTS.md - PlantProof Engineering & Architectural Guidelines

## 1. Project Overview & Mission
**PlantProof** is an enterprise multi-tenant regulatory intelligence and compliance-evidence management system engineered specifically for manufacturing organizations (initially focusing on Indian manufacturing jurisdictions such as Maharashtra, Gujarat, and Central statutes including MPCB, MoEFCC, DISH/Labour, PESO, and CPCB).

The platform bridges official government notifications, enterprise operational master data, deterministic rule-based applicability, AI-assisted document verification, human-in-the-loop auditability, and executive readiness reporting.

---

## 2. Core Non-Negotiable Tenets

### 2.1 The Cardinal Regulatory Rule
> **"AI Proposes, Humans Dispose."**
- Artificial Intelligence must **never** silently publish legal interpretations, alter legal registers without human approval, or state that an enterprise is "legally compliant" in an absolute sense.
- Every regulatory change, requirement mapping, and extracted document parameter must carry:
  1. **Provenance:** Traceable origin (Gazette notification number, issuing authority, publication date, clause reference, official PDF link).
  2. **Review Status:** Explicit state (`PROPOSED`, `PENDING_REVIEW`, `ACCEPTED`, `OVERRIDDEN`, `REJECTED`).
  3. **Audit Trail:** Identification of the user who confirmed or edited the proposal, with timestamp and rationale.

### 2.2 The Cardinal UX Rule
> **"No Raw Machine Artifacts in Customer-Facing Views."**
- Never display raw JSON, JSON-tree viewers, raw API error payloads, stack traces, raw LLM prompt text, or raw database error dumps in user-facing views.
- All machine-generated and extracted data must be mapped into clean UI components:
  - Formatted badges and status indicators
  - Human-readable labels and descriptions
  - Confidence indicators (High, Medium, Low)
  - Actionable error banners with remediation guidance
  - Original document preview side-by-side with extracted fields

### 2.3 Architecture & System Boundaries
- **Modular Monolith:** Built as a single cohesive deployable repository with clean internal boundaries (`api`, `core`, `modules/applicability`, `modules/documents`, `modules/regulatory_intel`, `modules/tasks`, `modules/reporting`). Avoid microservices until throughput and organizational boundaries strictly require them.
- **Multi-Tenancy:** Schema or tenant-id scoped multi-tenancy. Every query and data access operation must enforce strict tenant isolation (`tenant_id` and `plant_id` boundary check).
- **Deterministic vs. Probabilistic Separation:**
  - *Deterministic Engine:* Decides formal statutory applicability using boolean rule trees evaluated against plant profile attributes.
  - *Probabilistic / AI Layer:* Extracts text, categorizes clauses, summarizes changes, and proposes candidate impacts. It feeds into the deterministic engine and human review queue.

---

## 3. Technology Stack Conventions

### 3.1 Backend
- **Language & Runtime:** Python 3.11+ / 3.13
- **Framework:** FastAPI with Pydantic v2 schemas and dependency injection.
- **ORM & Data Layer:** SQLAlchemy 2.0 (declarative models, explicit type annotations) and Alembic migrations.
- **Database:** PostgreSQL (with JSONB for flexible rule parameters, audited tables, and UUID primary keys).
- **Background Processing:** Redis with background worker abstractions (ARQ / Celery / RQ) with synchronous fallback for local zero-dependency testing.
- **External Providers Interface Pattern:**
  - `DocumentParserProvider` (Abstract base: Local heuristic/PyPDF parser adapter + Google Document AI / Cloud Vision / Gemini Vision adapter).
  - `RegulatoryLLMProvider` (Abstract base: Mock/heuristic extractor + Gemini 1.5/2.0 / OpenAI adapter).
  - `StorageProvider` (Abstract base: Local filesystem storage adapter + AWS S3 / Google Cloud Storage adapter).

### 3.2 Frontend
- **Framework:** React 18+ with TypeScript (strict mode enabled).
- **Build Tool:** Vite with fast HMR.
- **Styling:** Modern, enterprise-grade Vanilla CSS / CSS Modules with cohesive design tokens (Dark Forest green `#06281e`, emerald `#059669`, slate grays, clean typography, glassmorphism badges, accessible contrast).
- **State & Data Fetching:** TanStack Query (React Query) for server state caching and optimism; lightweight state for local UI.
- **Icons & Visualization:** Lucide React icons, SVG/Canvas based charts (responsive donut, bar charts).
- **Accessibility:** WCAG 2.1 AA compliant colors, keyboard navigation, aria-labels on buttons and modals.

---

## 4. Coding & Workflow Standards for Agents

1. **Verify Before Modifying:** Always inspect existing schemas, tests, and endpoints before introducing changes.
2. **Database Migrations:** Never make ad-hoc schema modifications in code without a corresponding Alembic migration.
3. **Strict Validation:** Validate all incoming requests with Pydantic models. Sanitize inputs and validate file upload MIME types and size limits.
4. **Testing Discipline:**
   - Unit tests for all business logic (applicability rules, date calculations, validation checks).
   - Integration tests for API routes using `pytest` and `httpx.AsyncClient`.
   - Frontend component and utility tests.
5. **No Placeholders in Delivered Files:** Use real logic, robust fallback implementations, and descriptive typing instead of dummy `pass` or `TODO` shortcuts.
