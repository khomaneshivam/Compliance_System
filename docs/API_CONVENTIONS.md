# PlantProof: REST API Conventions & OpenAPI Usage Guide

**System Version:** v1.0.0  
**API Prefix:** `/api/v1`  
**OpenAPI Specification:** `http://localhost:8000/openapi.json`  
**Interactive Swagger UI:** `http://localhost:8000/docs`  
**Interactive ReDoc UI:** `http://localhost:8000/redoc`  
**Status:** Grounded in Active FastAPI Application Routes  

---

## 1. Overview & Architecture Standards

All PlantProof endpoints follow standard RESTful conventions:
- **Protocol:** HTTP/1.1 and HTTP/2 over TLS in production; local development on `http://127.0.0.1:8000`.
- **Resource Naming:** Lowercase, plural nouns separated by hyphens (e.g., `/master-data/document-types`, `/regulatory/changes`).
- **HTTP Methods:**
  - `GET`: Idempotent read operations (never mutate state).
  - `POST`: Create entities, trigger jobs, execute transitions, or submit credentials.
  - `PUT` / `PATCH`: Idempotent full replacement (`PUT`) or selective field updates (`PATCH`).
  - `DELETE`: Remove entities (where soft deletion or cascade deletion is permitted).

---

## 2. Authentication & Header Specifications

### 2.1 Request Headers

| Header | Format | Required | Purpose |
| :--- | :--- | :---: | :--- |
| `Authorization` | `Bearer <jwt_token>` | Protected endpoints | Authenticates user identity, tenant scope, and role claims. |
| `Content-Type` | `application/json` or `multipart/form-data` | On POST/PATCH/PUT | Declares payload serialization format. |
| `X-Correlation-ID` | Alphanumeric (1–64 chars: `^[a-zA-Z0-9_\-]{1,64}$`) | Optional | Distributed request tracing. If omitted or invalid, the gateway generates a fresh UUID. |

### 2.2 Response Headers

Every HTTP response includes defense-in-depth security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Correlation-ID: <uuid>` (Echoes or assigns request correlation identifier)
- `Retry-After: <seconds>` (Included on HTTP 429 rate limit responses)

---

## 3. Standard Response Envelopes & Error Handling

### 3.1 Paginated Collection Schema
All collection endpoints implement server-side pagination with bounded page sizes (default: 10, maximum: 100):
```json
{
  "items": [ ... ],
  "total": 48,
  "page": 1,
  "page_size": 10,
  "total_pages": 5
}
```

### 3.2 Standard Error Envelope
In accordance with the **Cardinal UX Rule**, no raw Python tracebacks or internal database errors are exposed:
```json
{
  "error": {
    "code": "TENANT_ACCESS_DENIED",
    "message": "User does not have permission to access facilities in organization 'Beta Pharma'.",
    "remediation": "Verify your active tenant credentials or request access from your enterprise administrator.",
    "correlation_id": "40f52630-a15f-4ace-b34e-da03427c61ae"
  }
}
```

---

## 4. Rate Limiting Policy

To protect authentication, storage vaults, and CPU resources, the following sliding-window limits are enforced:
- `POST /api/v1/auth/login`: **15 requests / minute / IP**
- `POST /api/v1/documents/upload`: **30 requests / minute / IP**
- `POST /api/v1/reports`: **15 requests / minute / IP**

When exceeded, the server returns `HTTP 429 Too Many Requests` with a `Retry-After` header indicating seconds until the window slides.

---

## 5. Complete Endpoint Inventory (72 Endpoints)

### 5.1 Identity & Access Management (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Authenticate with email/password; returns JWT access token.
- `GET /api/v1/auth/me`: Fetch active user profile, tenant details, and assigned plants.
- `GET /api/v1/auth/users`: List team members in the authenticated tenant.
- `POST /api/v1/auth/users/invite`: Provision a new user (restricted to `ADMIN` or `SUPER_ADMIN`).

### 5.2 Facility & Operational Profile (`/api/v1/companies` & `/api/v1/plants`)
- `POST /api/v1/companies`: Register a new plant facility (restricted to `ADMIN` / `PLANT_MANAGER`).
- `GET /api/v1/companies`: List accessible facilities for the tenant.
- `GET /api/v1/companies/{id}/profile`: Fetch plant operational profile and capacity attributes.
- `PATCH /api/v1/companies/{id}/profile`: Update facility parameters (triggers audit log).
- `POST /api/v1/companies/{id}/profile-with-reassessment`: Apply profile updates and immediately evaluate new statutory obligations.
- `POST /api/v1/companies/{id}/simulate-reassessment`: Dry-run simulation returning candidate requirement diffs without modifying registers.
- `POST /api/v1/companies/{id}/assessments`: Run deterministic applicability assessment.
- `GET /api/v1/companies/{id}/gaps`: Summarize missing, expired, and non-compliant requirements.
- `GET /api/v1/plants`: List facilities with summary compliance metrics.
- `GET /api/v1/plants/{id}`: Fetch single facility detail.
- `GET /api/v1/plants/{id}/equipment`: List equipment inventory (boilers, DG sets, ETP).
- `POST /api/v1/plants/{id}/equipment`: Register a new equipment asset.
- `GET /api/v1/plants/{id}/profile`: Direct profile query.
- `PUT /api/v1/plants/{id}/profile`: Direct profile update.

### 5.3 Active Requirements Register (`/api/v1/requirements`)
- `GET /api/v1/requirements`: Paginated, filtered, searchable requirements register.
- `GET /api/v1/requirements/saved-views`: Presets for filter views (e.g., `Due in 30 Days`, `Missing Evidence`).
- `GET /api/v1/requirements/{id}`: Detailed requirement view with statutory provenance, history, and evidence links.

### 5.4 Evidence & Document Vault (`/api/v1/documents`)
- `POST /api/v1/documents/upload`: Upload scanned certificate (PDF, JPG, PNG) with MIME and 25MB validation.
- `GET /api/v1/documents`: List uploaded evidence documents for a plant.
- `GET /api/v1/documents/{id}`: Fetch document metadata, extracted fields, and validation checks.
- `GET /api/v1/documents/{id}/file`: Securely stream original document file from vault.
- `GET /api/v1/documents/{id}/fields`: Fetch AI-extracted parameters and confidence scores.
- `POST /api/v1/documents/{id}/review`: Human review action (`APPROVED`, `REJECTED`, or `EDITED_AND_APPROVED`).
- `POST /api/v1/documents/{id}/re-extract`: Trigger re-extraction on an uploaded document.
- `GET /api/v1/documents/{id}/history`: Fetch immutable audit history for document reviews.

### 5.5 Regulatory Intelligence (`/api/v1/regulatory`)
- `GET /api/v1/regulatory/sources`: List official government gazette sources and adapters.
- `GET /api/v1/regulatory/sources/{id}/health`: Check polling health and uptime status.
- `POST /api/v1/regulatory/sources/{id}/poll`: Trigger manual ingestion check for a source.
- `GET /api/v1/regulatory/changes`: List published regulatory circulars and amendments.
- `GET /api/v1/regulatory/changes/{id}`: Fetch single regulatory notification details.
- `GET /api/v1/regulatory/changes/{id}/impacts`: Fetch tenant-scoped plant impacts.
- `POST /api/v1/regulatory/changes/{id}/review`: Human sign-off on regulatory change impact.
- `GET /api/v1/regulatory/changes/{id}/history`: Provenance and review audit log for a change.

### 5.6 Admin Rule Management (`/api/v1/admin/rules`)
- `GET /api/v1/admin/rules`: List global statutory applicability rules.
- `POST /api/v1/admin/rules`: Author a new statutory rule draft.
- `POST /api/v1/admin/rules/{id}/approve`: Approve candidate rule draft into active catalog.
- `POST /api/v1/admin/rules/{id}/supersede`: Publish a new rule version that supersedes an existing rule.
- `GET /api/v1/admin/rules/{id}/versions`: View complete version history and AST diffs for a rule.

### 5.7 Remediation Tasks (`/api/v1/tasks`)
- `GET /api/v1/tasks`: Paginated, filtered remediation task listing.
- `POST /api/v1/tasks`: Create a new compliance remediation task.
- `GET /api/v1/tasks/{id}`: Fetch task details with comments and attachments.
- `PATCH /api/v1/tasks/{id}`: Update task title, description, priority, or assignee.
- `POST /api/v1/tasks/{id}/status`: Controlled state transition (`TODO` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `BLOCKED` $\rightarrow$ `COMPLETED`).
- `POST /api/v1/tasks/{id}/comments`: Post comment to task discussion thread.
- `POST /api/v1/tasks/{id}/attachments/link`: Link existing vault document to a task.
- `POST /api/v1/tasks/{id}/attachments/upload`: Upload supporting evidence file directly to a task.

### 5.8 Reminders & Notifications (`/api/v1/reminders`)
- `GET /api/v1/reminders/notifications`: List in-app notifications and unread counts.
- `PATCH /api/v1/reminders/notifications/{id}/read`: Mark single notification as read.
- `POST /api/v1/reminders/notifications/read-all`: Mark all notifications as read.
- `GET /api/v1/reminders/preferences`: Fetch user alert preferences.
- `PUT /api/v1/reminders/preferences`: Update alert thresholds and channels.
- `POST /api/v1/reminders/run-scheduler`: Trigger on-demand evaluation of due-soon and overdue items.
- `POST /api/v1/reminders/test-notification`: Dispatch test alert through notification adapter.

### 5.9 Executive Readiness Reports (`/api/v1/reports`)
- `POST /api/v1/reports`: Configure and trigger readiness report generation (HTML/JSON).
- `GET /api/v1/reports`: List generated reports for a facility.
- `GET /api/v1/reports/{id}`: Check report job generation status and metrics snapshot.
- `GET /api/v1/reports/{id}/download`: Download generated HTML/JSON dossier with security validation.

### 5.10 Master Data Catalog (`/api/v1/master-data`)
- `GET /api/v1/master-data/authorities`: List statutory bodies (MPCB, DISH, CPCB).
- `GET /api/v1/master-data/acts`: List statutory acts and codes.
- `GET /api/v1/master-data/requirements`: List standard legal obligations.
- `GET /api/v1/master-data/requirements/{code}`: Fetch requirement definition by code.
- `GET /api/v1/master-data/jurisdictions`: List supported states and central scopes.
- `GET /api/v1/master-data/industry-categories`: List CPCB categorization criteria.
- `GET /api/v1/master-data/document-types`: List standard evidence document types.
- `GET /api/v1/master-data/activities`: List business activities.

### 5.11 Audit & Health Probes (`/api/v1/admin/audit-logs` & `/api/v1/health`)
- `GET /api/v1/admin/audit-logs`: Query immutable system audit logs with actor and diff filters.
- `GET /api/v1/health`: Overall system health and component check (database, vault).
- `GET /api/v1/health/liveness`: Kubernetes/container liveness probe.
- `GET /api/v1/health/readiness`: Database responsive readiness probe.
