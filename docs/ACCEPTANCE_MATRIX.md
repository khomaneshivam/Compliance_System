# PlantProof: Requirement Traceability & Acceptance Matrix
**Document Version:** 1.0.0  
**Status:** Approved for Implementation Planning  
**Coverage:** 100% Core Requirements Mapped to Modules, Entities, Routes, Tests, and Documentation

---

## 1. Master Traceability Matrix

| Req ID | Requirement Description | Architecture Module | Data Entities | API Routes | UI View / Screen | Test Suite Reference | Documentation Ref |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-01** | Multi-tenant isolation & plant scoping | `core.tenancy`, `api.auth` | `Tenant`, `User`, `Plant` | `POST /auth/login`<br>`GET /auth/me`<br>`GET /plants` | Global Header, Plant Selector | `test_auth_tenancy.py`<br>`test_plant_isolation.py` | `docs/ARCHITECTURE.md#tenancy` |
| **REQ-02** | Plant operational profile & master parameters | `modules.plant_profile` | `PlantProfile`, `PlantEquipment` | `GET /plants/{id}/profile`<br>`PUT /plants/{id}/profile`<br>`GET /plants/{id}/equipment` | Company Profile (`/company-profile`) | `test_plant_profile.py` | `docs/USER_GUIDE.md#company-profile` |
| **REQ-03** | Master regulatory statutory catalog | `modules.catalog` | `RegulatoryAuthority`, `RegulatoryAct`, `StatutoryRequirement` | `GET /catalog/requirements`<br>`GET /catalog/requirements/{id}` | Requirements Register (`/requirements`) | `test_catalog_seed.py` | `docs/STATUTORY_CATALOG.md` |
| **REQ-04** | Deterministic applicability rules engine | `modules.applicability` | `ApplicabilityRule`, `PlantRequirement` | `POST /plants/{id}/evaluate-applicability` | Register Applicability Badges | `test_rules_engine.py`<br>`test_ast_evaluator.py` | `docs/RULES_ENGINE.md` |
| **REQ-05** | Requirements register with filters & pagination | `modules.requirements` | `PlantRequirement`, `EvidenceLink` | `GET /plants/{id}/requirements`<br>`PATCH /plants/{id}/requirements/{id}` | Requirements Register (`/requirements`) | `test_requirements_api.py` | `docs/USER_GUIDE.md#register` |
| **REQ-06** | Real-time compliance dashboard & KPI calculation | `modules.dashboard` | `PlantRequirement`, `ComplianceTask`, `RegulatoryUpdate` | `GET /plants/{id}/requirements/summary` | Executive Dashboard (`/dashboard`) | `test_dashboard_kpis.py` | `docs/USER_GUIDE.md#dashboard` |
| **REQ-07** | Document upload & evidence vault | `modules.documents` | `ComplianceDocument` | `POST /plants/{id}/documents/upload`<br>`GET /documents/{id}/preview` | Document List (`/documents`) | `test_document_upload.py` | `docs/EVIDENCE_VAULT.md` |
| **REQ-08** | OCR & field extraction provider abstraction | `providers.document_parser` | `ExtractedField`, `ValidationCheck` | Provider interface methods | Document Review (`/documents/:id/review`) | `test_ocr_provider.py` | `docs/PROVIDER_INTERFACES.md` |
| **REQ-09** | Dual-pane document review & human sign-off | `modules.documents` | `ExtractedField`, `EvidenceLink` | `GET /documents/{id}/review`<br>`POST /documents/{id}/approve`<br>`POST /documents/{id}/reject` | Document Review (`/documents/:id/review`) | `test_document_review.py`<br>`e2e_document_flow.spec.ts` | `docs/USER_GUIDE.md#document-review` |
| **REQ-10** | Official regulatory change ingestion & detail | `modules.regulatory_intel` | `RegulatoryUpdate`, `AffectedRequirementMap` | `GET /regulatory-updates`<br>`GET /regulatory-updates/{id}` | Regulatory Changes (`/regulatory-changes/:id`) | `test_regulatory_intel.py` | `docs/REGULATORY_INTELLIGENCE.md` |
| **REQ-11** | Plant impact evaluation & human legal review | `modules.regulatory_intel` | `RegulatoryReview`, `ComplianceTask` | `GET /regulatory-updates/{id}/impact/{plant_id}`<br>`POST /regulatory-updates/{id}/review` | Regulatory Changes (`/regulatory-changes/:id`) | `test_change_impact.py` | `docs/REGULATORY_INTELLIGENCE.md#review` |
| **REQ-12** | Compliance remediation task workflows | `modules.tasks` | `ComplianceTask` | `GET /plants/{id}/tasks`<br>`POST /plants/{id}/tasks`<br>`PATCH /tasks/{id}` | Remediation Tasks (`/tasks`) | `test_tasks_api.py` | `docs/USER_GUIDE.md#tasks` |
| **REQ-13** | Readiness scoring & audit-proof export | `modules.reporting` | `PlantRequirement`, `AuditLog` | `GET /plants/{id}/reports/readiness`<br>`GET /plants/{id}/reports/export` | Reports View (`/reports`) | `test_readiness_report.py` | `docs/AUDIT_READINESS.md` |
| **REQ-14** | Complete audit logging & provenance | `core.audit` | `AuditLog` | Automated query hooks | System-wide audit trail | `test_audit_logging.py` | `docs/ARCHITECTURE.md#audit` |

---

## 2. Detailed Acceptance Criteria by Feature

### REQ-01: Multi-Tenant Isolation & Plant Scoping
- **Context:** An enterprise operates multiple manufacturing sites (e.g. Pune Facility, Nashik Unit).
- **Acceptance Criteria (Gherkin format):**
  - **AC-01.1 (Cross-Tenant Isolation):**  
    *Given* an authenticated user belonging to Tenant A,  
    *When* the user requests records with a `plant_id` belonging to Tenant B,  
    *Then* the system must return HTTP 403 Forbidden and log an unauthorized access attempt in `audit_logs`.
  - **AC-01.2 (Plant Switcher Scope):**  
    *Given* a user with access to "All Plants" and specific facilities,  
    *When* the user selects "All Plants" from the global dropdown,  
    *Then* the dashboard and registers aggregate metrics across all plants owned by their tenant.
  - **AC-01.3 (Role Boundaries):**  
    *Given* a user with role `VIEWER`,  
    *When* they attempt to POST or PATCH any resource,  
    *Then* the API returns HTTP 403 Forbidden with a clear customer-facing explanation ("You do not have permission to modify compliance records").

---

### REQ-02 & REQ-04: Deterministic Applicability Engine & Plant Profile
- **Context:** Deciding statutory applicability based on physical manufacturing parameters without LLM hallucinations.
- **Acceptance Criteria:**
  - **AC-04.1 (Boiler Act Applicability):**  
    *Given* a plant profile located in Maharashtra with `boiler_count = 1` and `steam_capacity_tph = 4.5`,  
    *When* the applicability engine executes,  
    *Then* statutory requirement `BOILER-INSP-CERT` (Boiler Inspection Certificate) is marked `APPLICABLE`,  
    *And* the rationale explains: "Applicable under Section 7 of the Indian Boilers Act, 1923 because this facility operates 1 boiler(s) with cumulative steam capacity of 4.5 TPH."
  - **AC-04.2 (Zero Boilers Exemption):**  
    *Given* a plant profile with `boiler_count = 0` and `steam_capacity_tph = 0`,  
    *When* the engine executes,  
    *Then* `BOILER-INSP-CERT` is marked `NOT_APPLICABLE` with the rationale "Not applicable as this facility operates no registered boilers or steam vessels."
  - **AC-04.3 (Conditionally Applicable):**  
    *Given* a plant profile in the Red/Chemical category with proposed expansion pending EIA screening,  
    *When* the engine executes,  
    *Then* `ENV-CLEARANCE` is marked `CONDITIONALLY_APPLICABLE`.

---

### REQ-05 & REQ-06: Requirements Register & Executive Dashboard
- **Context:** High-visibility compliance command center matching the approved high-fidelity design.
- **Acceptance Criteria:**
  - **AC-05.1 (Register Columns & Badges):**  
    *Given* the user navigates to `/requirements`,  
    *Then* the table displays: Requirement Name, Authority, Applicability (with green/blue pill), Evidence Status (with green/amber/red pill), Due Date, and Owner (with avatar and title).
  - **AC-05.2 (Faceted Filtering):**  
    *Given* 48 total requirements,  
    *When* the user filters by Jurisdiction="Maharashtra", Industry="All Industries", and Status="Missing",  
    *Then* only the matching records (e.g. "Consent to Operate", "Hazardous Waste Authorisation") are displayed with active filter count.
  - **AC-06.1 (Dashboard KPI Accuracy):**  
    *Given* Acme Manufacturing's compliance register,  
    *When* the dashboard loads,  
    *Then* it renders:
      - 48 Requirements (36 applicable, 12 not applicable)
      - 12 Due Soon (Next 30 days)
      - 8 Evidence Gaps (Missing or expired)
      - 5 Regulatory Changes (2 requiring review)
      - Compliance Status Donut Chart displaying 75% compliant
      - 6-Month Upcoming Deadlines Bar Chart.
  - **AC-06.2 (Needs Attention Urgency Queue):**  
    *Given* requirements with overdue or near-term due dates,  
    *Then* the "Needs Attention" card lists overdue items (e.g. Consent to Operate, 15 Oct 2025, Overdue) in prioritized order with direct action links.

---

### REQ-08 & REQ-09: AI-Assisted Document Extraction & Human Review Flow
- **Context:** The Cardinal Regulatory Rule: "AI Proposes, Humans Dispose".
- **Acceptance Criteria:**
  - **AC-09.1 (Dual-Pane Rendering):**  
    *Given* an uploaded document in status `PENDING_REVIEW`,  
    *When* the user navigates to `/documents/:id/review`,  
    *Then* the screen renders the rendered inspection certificate on the left pane and the extracted parameters on the right pane.
  - **AC-09.2 (Field Confidence Indicators):**  
    *Given* extracted fields (Certificate Number: `MH/B/2025/1042`, Authority: `Chief Inspector of Boilers`, Equipment: `Steam Boiler`, Inspection Date: `15 Jun 2025`, Valid Until: `14 Jun 2026`),  
    *Then* each field renders with its confidence rating badge (`High` green pill, `Medium` amber pill).
  - **AC-09.3 (Deterministic Validation Checks):**  
    *Then* the UI displays verified checks with green checkmarks:
      - Document type identified
      - Dates are valid
      - Certificate number format is valid
      - Matches equipment in register.
  - **AC-09.4 (Inline Human Editing):**  
    *When* the user clicks "Edit Details",  
    *Then* all fields become editable inputs, allowing the reviewer to correct OCR misreadings before sign-off.
  - **AC-09.5 (Approval State Transition):**  
    *When* the user clicks "Approve Document",  
    *Then* the document status transitions to `APPROVED`, an immutable audit log is generated with the reviewer's ID, and the linked requirement status transitions from `EXPIRING_SOON` / `MISSING` to `VALID`.
  - **AC-09.6 (Rejection Flow):**  
    *When* the user clicks "Reject",  
    *Then* a modal prompts for a mandatory rejection rationale; upon confirmation, status becomes `REJECTED`, the requirement remains deficient, and a remediation task is queued.

---

### REQ-10 & REQ-11: Regulatory Change Intelligence & Impact Evaluation
- **Context:** Official gazette change tracking with human-in-the-loop review.
- **Acceptance Criteria:**
  - **AC-10.1 (Structured Intelligence Detail):**  
    *Given* regulatory update "Amendment to Hazardous Waste Management Rules, 2016",  
    *When* the user opens the detail page,  
    *Then* the page displays: Authority (MoEFCC), Notification No. (S.O. 1234(E)), Published Date (12 Sep 2025), Effective Date (01 Dec 2025), "What Changed?" explainer, "Key Changes" bulleted list, and "Official Source" link to the original Gazette PDF.
  - **AC-11.1 (Enterprise Impact Matcher):**  
    *Given* Acme Manufacturing's plant profile (which generates and stores hazardous waste in Maharashtra),  
    *Then* the "Your Business Impact" card alerts: "This change may apply to your plant based on your current operations. Please review and confirm applicability."
  - **AC-11.2 (Mandatory Human Sign-off):**  
    *When* the Plant Manager clicks "Mark as Reviewed" and confirms the review modal,  
    *Then* the regulatory update status transitions to `REVIEWED`, an audit event is stamped, and any associated action items appear under `/tasks`.

---

## 3. Non-Functional Acceptance Criteria

### 3.1 UX Integrity (Zero Raw Machine Artifacts)
- **NF-UX-01:** Customer-facing screens must never expose raw JSON snippets, raw `{ "error": ... }` bodies, raw database exceptions, or unformatted timestamps.
- **NF-UX-02:** All dates must be formatted in clear enterprise locale format (e.g. `15 Oct 2025`, `14 Jun 2026`).
- **NF-UX-03:** All interactive controls (buttons, inputs, dropdowns) must provide visual hover and focus states, meeting WCAG 2.1 AA accessibility contrast standards.

### 3.2 Security & Data Privacy
- **NF-SEC-01:** All file uploads must be scanned for allowed MIME types (`application/pdf`, `image/png`, `image/jpeg`) and restricted to maximum 20MB.
- **NF-SEC-02:** Password hashing using bcrypt or Argon2 with strong salt work factors.
- **NF-SEC-03:** JWT access tokens signed with HMAC-SHA256 and configured with 1-hour expiration and refresh mechanics.

### 3.3 Performance & Reliability
- **NF-PERF-01:** Requirements Register initial load and filtering must render in under 400ms for registers with up to 1,000 items.
- **NF-PERF-02:** Document preview rendering must display within 1.5 seconds on broadband connections.
- **NF-PERF-03:** Applicability rules engine execution for a plant profile must complete in under 150ms.

---

## 4. Test Strategy & Coverage Thresholds

| Test Level | Scope | Target Coverage | Framework / Tool |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | Rules engine AST evaluator, date calculations, validation check functions, Pydantic model serializers. | >= 90% | `pytest`, `pytest-cov` |
| **API Integration** | FastAPI endpoints, auth middleware, tenant isolation, database transactions, error responses. | >= 85% | `pytest`, `httpx.AsyncClient` |
| **Component UI Tests** | Badges, status pills, filter bar, document previewer, metric cards, action modals. | >= 80% | `vitest`, `@testing-library/react` |
| **End-to-End Tests** | Full flows: Login -> View Dashboard -> Filter Register -> Upload & Review Document -> Confirm Regulatory Change. | Core User Flows | Playwright / synthetic scenario runner |

---

## 5. Definition of Done (DoD) per Phase

For any phase to be considered complete and ready for sign-off:
1. **Code Quality:** All Python code formatted with Ruff/Black; TypeScript compiles cleanly with zero type errors (`tsc --noEmit`).
2. **Automated Testing:** All unit and integration tests passing in CI/local test suite.
3. **Regulatory Tenet Adherence:** Provenance fields present on all regulatory records; review state machine strictly enforced.
4. **UX Tenet Adherence:** Zero raw JSON, stack traces, or raw error strings in any rendered UI view.
5. **Documentation:** OpenAPI documentation updated; corresponding section in `docs/` updated.
