# PlantProof: Detailed Screen Specifications & Interaction Contracts
**Document Version:** 1.0.0  
**Scope:** 18 Core Application Screens & Global App States  
**Visual Reference:** [PlantProof UI Reference](file:///d:/Complaince%20System/docs/design/PlantProof_UI_Reference.png)  
**Design System Standards:** [Design System Guide](file:///d:/Complaince%20System/docs/design/DESIGN_SYSTEM.md)

---

## Screen Inventory Overview

| Screen # | Screen Name | Route Path | Primary User Persona | Access Level |
| :---: | :--- | :--- | :--- | :--- |
| **01** | Sign In / Invite Acceptance / Password Reset | `/auth/login`, `/auth/accept-invite`, `/auth/reset-password` | All Users | Public / Token |
| **02** | First-Run Company Setup Wizard | `/setup-wizard` | Facility Admin, Plant Manager | Authenticated (New Tenant) |
| **03** | Executive Compliance Dashboard | `/dashboard` | Plant Manager, EHS Director | Authenticated |
| **04** | Master Requirements Register | `/requirements` | EHS Manager, Facility Admin | Authenticated |
| **05** | Requirement Detail & Evidence Audit | `/requirements/:id` | EHS Manager, Auditor | Authenticated |
| **06** | Document Evidence Vault | `/documents` | EHS Staff, Admin | Authenticated |
| **07** | Dual-Pane Document Review Workspace | `/documents/:id/review` | EHS Manager, Plant Manager | Authenticated (Reviewer) |
| **08** | Regulatory Change Inbox | `/regulatory-changes` | Legal, EHS Manager | Authenticated |
| **09** | Regulatory Change Detail & Diff Inspector | `/regulatory-changes/:id` | Plant Manager, General Counsel | Authenticated |
| **10** | Company Impact Assessment | `/regulatory-changes/:id/impact` | Plant Manager, EHS Director | Authenticated |
| **11** | Tasks & Deadlines (List & Calendar) | `/tasks` | All Facility Staff | Authenticated |
| **12** | Audit & Readiness Report Builder | `/reports/builder` | Compliance Auditor, Plant Head | Authenticated |
| **13** | Company Operational Profile & Facts | `/company-profile` | Plant Manager, Operations Lead | Authenticated (Manager) |
| **14** | Master Data Administration | `/admin/master-data` | System Admin | Admin Only |
| **15** | Rule Authoring & Test Bench | `/admin/rules` | Regulatory Architect, Legal Lead | Admin Only |
| **16** | Users, Roles & Permissions | `/admin/users` | Tenant Admin | Admin Only |
| **17** | Compliance Intelligence Search | `/search` (or Modal `Ctrl+K`) | All Users | Authenticated |
| **18** | Global Application States | System-wide | All Users | System-wide |

---

## Detailed Specifications

---

### Screen 01: Sign In / Invite Acceptance / Password Reset

- **Objective:** Provide a secure, friction-free login, invite onboarding, and password recovery interface for factory personnel.
- **Primary User:** All corporate and plant users.
- **Visual Hierarchy:**
  - Centered clean card container (`max-width: 440px`) on light neutral canvas (`#f8fafc`).
  - PlantProof brand badge with emerald leaf icon.
  - Tabbed or dedicated modes: Sign In, Forgot Password, Accept Team Invite.
- **Components:**
  - Email input with format validation.
  - Password input with toggleable show/hide eye icon.
  - "Remember me" checkbox and "Forgot password?" link.
  - Primary button: "Sign In to PlantProof".
  - Alert banner for failed authentication (e.g. *"Incorrect email or password. Please verify your credentials."*).
- **Main Actions:**
  - `Submit Login` $\rightarrow$ Authenticates via `/api/v1/auth/login`, stores JWT in secure storage, redirects to `/dashboard`.
  - `Accept Invite` $\rightarrow$ Validates invite token, collects full name and new password, creates account.
- **States:**
  - *Loading:* Button shows spinner with label *"Authenticating..."*.
  - *Error:* Red alert banner at top of card; input field border turns red.
- **Keyboard Navigation:** `Enter` key submits form; `Tab` cycles inputs cleanly.
- **API Dependencies:** `POST /api/v1/auth/login`, `POST /api/v1/auth/accept-invite`, `POST /api/v1/auth/reset-password`.
- **Destructive Actions:** None.

---

### Screen 02: First-Run Company Setup Wizard

- **Objective:** Guide new enterprise tenants through configuring their manufacturing profile to initialize the deterministic applicability engine.
- **Primary User:** Facility Administrator, Plant Manager.
- **Visual Hierarchy:**
  - Stepper indicator across top:
    1. Legal Entity & State $\rightarrow$ 2. Sites & Facilities $\rightarrow$ 3. Industry & CPCB Category $\rightarrow$ 4. Operational Facts & Capacities $\rightarrow$ 5. Review & Confirm
  - Main configuration card with clear form fields and context tooltips.
  - Sticky bottom navigation bar: "Back" (secondary) and "Save & Continue" (primary).
- **Components:**
  - Jurisdiction selector: Maharashtra (MPCB), Gujarat (GPCB), Central/National.
  - Industry categorization radio cards: **RED** (Heavy pollution/chemical), **ORANGE**, **GREEN**, **WHITE**.
  - Equipment facts: Boilers (steam capacity TPH), DG sets (kVA), Effluent discharge (KLD).
  - Workforce facts: Permanent headcount, contract labour count.
  - Review screen with summary card and "Generate Requirements Register" CTA.
- **Main Actions:**
  - `Step Forward` $\rightarrow$ Validates step data.
  - `Finalize Setup` $\rightarrow$ Submits to `/api/v1/plants/{id}/profile`, triggers applicability engine, redirects to `/dashboard`.
- **States:**
  - *Empty:* Pre-filled with reasonable defaults (e.g. employee count = 0).
  - *Error:* Inline error message under required fields (e.g. *"Please specify connected load in kW"*).
- **API Dependencies:** `POST /api/v1/plants`, `PUT /api/v1/plants/{id}/profile`, `POST /api/v1/plants/{id}/evaluate-applicability`.
- **Destructive Actions:** None.

---

### Screen 03: Executive Compliance Dashboard (`/dashboard`)

- **Objective:** Give factory managers instantaneous situational awareness of overall compliance readiness, upcoming deadlines, evidence gaps, and required human reviews.
- **Primary User:** Plant Manager (e.g. Rohit Sharma), EHS Director (e.g. Priya Deshmukh).
- **Visual Hierarchy:**
  - **Header:** "Dashboard - Your compliance overview and key actions" + Facility Switcher dropdown ("All Plants", "Pune Facility").
  - **Stat Cards Row (4 cards):**
    1. *Requirements:* 48 Total (36 applicable, 12 not applicable)
    2. *Due Soon:* 12 in Next 30 days (+3 from last month)
    3. *Evidence Gaps:* 8 missing or expired (+2 from last month)
    4. *Regulatory Changes:* 5 relevant (2 require human review)
  - **Mid Analytics (2 side-by-side cards):**
    - *Compliance Status Donut:* SVG ring showing 75% Compliant + color-coded breakdown (Compliant 36, Due Soon 12, Overdue 6, Not Applicable 8).
    - *Upcoming Deadlines Bar Chart:* 6-month histogram (Oct: 12, Nov: 8, Dec: 6, Jan: 9, Feb: 4, Mar: 2).
  - **Bottom Queue ("Needs Attention"):** Priority list with overdue and due soon badges, authority names, due dates, and owner avatars.
- **Main Actions:**
  - Click on "Evidence Gaps" card $\rightarrow$ Filters Requirements Register by `status=Missing`.
  - Click on "Needs Attention" item $\rightarrow$ Opens Requirement Detail or Document Review view.
  - "View All" link $\rightarrow$ Navigates to `/requirements`.
- **States:**
  - *Loading:* Skeleton cards and skeleton donut ring.
  - *Empty:* Renders "All statutory permits are up to date" celebration card when 0 items need attention.
- **API Dependencies:** `GET /api/v1/plants/{id}/requirements/summary`.
- **Destructive Actions:** None.

---

### Screen 04: Master Requirements Register (`/requirements`)

- **Objective:** Maintain the single source of truth for all statutory obligations, consents, licenses, and inspection certificates.
- **Primary User:** EHS Manager, Compliance Auditor.
- **Visual Hierarchy:**
  - **Page Header:** Title + Actions: "Export Register" (CSV/PDF) and "+ Add Custom Requirement" (primary teal).
  - **Filter Toolbar:**
    - Jurisdiction dropdown (Maharashtra, Gujarat, Central).
    - Industry filter (All Industries, Chemicals, Manufacturing).
    - Status filter (All Statuses, Valid, Missing, Expiring Soon, Overdue, Conditionally Applicable).
    - Search text input with real-time filter.
  - **Data Table (Columns):**
    1. Requirement Name (e.g. "Consent to Operate", "Boiler Inspection Certificate")
    2. Authority (e.g. "Maharashtra Pollution Control Board", "Chief Inspector of Boilers")
    3. Applicability (with green/blue pill: `Applicable`, `Conditionally Applicable`)
    4. Evidence Status (with green/amber/red pill: `Valid`, `Expiring Soon`, `Missing`)
    5. Due Date (formatted: `15 Oct 2025`, `28 Oct 2025`)
    6. Owner (avatar with initials + full name)
    7. Row Actions (`...` dropdown: View details, Upload evidence, Re-evaluate, Assign task)
  - **Pagination Bar:** "Showing 1-10 of 48 requirements" + page navigation buttons.
- **Main Actions:**
  - Filter / Sort / Paginate.
  - Click row $\rightarrow$ Opens Requirement Detail (`/requirements/:id`).
  - Click "+ Add Custom Requirement" $\rightarrow$ Opens modal.
- **States:**
  - *Empty State:* "No requirements match your active filters. [Clear Filters]".
- **API Dependencies:** `GET /api/v1/plants/{id}/requirements?page=1&status=Missing`.
- **Destructive Actions:** Archiving a requirement requires explicit confirmation modal.

---

### Screen 05: Requirement Detail & Evidence Audit (`/requirements/:id`)

- **Objective:** Provide a deep dive into an individual statutory obligation with plain-language explanations, legal clause citations, active evidence links, and audit history.
- **Primary User:** EHS Manager, Corporate Auditor.
- **Visual Hierarchy:**
  - Breadcrumb: `<- Back to Requirements Register`.
  - Header: Requirement Code & Title (e.g. `BOILER-INSP-CERT - Boiler Inspection Certificate`) + Status Badges.
  - Tabbed body:
    1. *Overview & Applicability:* Why this applies to Acme Manufacturing, operational criteria matched, statutory act and section reference.
    2. *Evidence & Documents:* Attached certificate preview, issue date, valid until date, verification status.
    3. *Audit Trail & History:* Complete immutable timeline of who uploaded evidence, when it was verified, and when rules were re-evaluated.
- **Main Actions:**
  - `Upload New Evidence Document` $\rightarrow$ Triggers upload modal.
  - `Re-evaluate Applicability` $\rightarrow$ Executes rules engine for this single requirement.
  - `Reassign Owner` $\rightarrow$ Changes responsible team member.
- **API Dependencies:** `GET /api/v1/plants/{id}/requirements/{id}`, `PATCH /api/v1/plants/{id}/requirements/{id}`.
- **Destructive Actions:** Unlinking an approved evidence document requires confirmation.

---

### Screen 06: Document Evidence Vault (`/documents`)

- **Objective:** Provide an organized repository of all uploaded statutory certificates, inspection reports, and consent letters.
- **Primary User:** EHS Staff, Operations Admin.
- **Visual Hierarchy:**
  - Header: Title + "+ Upload Document" button.
  - View toggle: Tabular List view (default) vs Grid Card view.
  - Filter bar: Document type, review status (`Pending Review`, `Approved`, `Rejected`), upload date range.
  - Document Table: Filename, Document Type, Plant / Facility, Upload Date, File Size, Review Status Badge, Actions (Preview, Review, Download).
- **Main Actions:**
  - `Upload Document` $\rightarrow$ Drag-and-drop file upload zone (validates file size < 20MB, allowed types: PDF, PNG, JPG).
  - Click `Review` $\rightarrow$ Opens Screen 07 (Dual-Pane Review Workspace).
- **API Dependencies:** `GET /api/v1/plants/{id}/documents`, `POST /api/v1/plants/{id}/documents/upload`.
- **Destructive Actions:** Deleting a document requires confirmation; approved documents linked to active requirements cannot be deleted without unlinking.

---

### Screen 07: Dual-Pane Document Review Workspace (`/documents/:id/review`)

- **Objective:** Enable EHS managers to verify AI/OCR-extracted certificate parameters side-by-side with the official source document before formal sign-off (*The Cardinal Regulatory Rule: "AI Proposes, Humans Dispose"*).
- **Primary User:** EHS Manager (e.g. Priya Deshmukh), Plant Manager.
- **Visual Hierarchy:**
  - Breadcrumb: `<- Back to Documents` + Status badge (`Pending Review`) + Document counter (`Document 1 of 5` with prev/next arrows).
  - Subtitle: "Verify extracted information and approve or edit the document details".
  - **Left Pane (50% width):** Interactive Document Viewer:
    - PDF / Image previewer with pan and zoom controls (`- 100% +`), page counter, fullscreen toggle.
    - Displays native certificate (e.g. Government of Maharashtra Chief Inspector of Boilers Form).
  - **Right Pane (50% width):** Extracted Data & Validation:
    - **Extracted Information Group:**
      - Document Type: "Boiler Inspection Certificate" (Confidence: `High` green badge)
      - Certificate No: "MH/B/2025/1042" (Confidence: `High`)
      - Authority: "Chief Inspector of Boilers" (Confidence: `High`)
      - Equipment: "Steam Boiler" (Confidence: `High`)
      - Inspection Date: "15 Jun 2025" (Confidence: `High`)
      - Valid Until: "14 Jun 2026" (Confidence: `High`)
      - Issuing Location: "Maharashtra" (Confidence: `Medium` amber badge)
      - "Edit All" button allowing inline field editing.
    - **Validation Checks Group:**
      - Checkmark: Document type identified
      - Checkmark: Dates are valid
      - Checkmark: Certificate number format is valid
      - Checkmark: Matches equipment in register
    - **Bottom Action Bar:**
      - `Reject` button (secondary danger): prompts for mandatory rejection reason.
      - `Edit Details` button (secondary outline): switches inputs to editable state.
      - `Approve Document` button (primary teal/green): commits approval, updates requirement status to `VALID`.
- **Main Actions:**
  - `Inline Edit`: Fix any OCR misreadings.
  - `Approve`: Commits approval with reviewer ID and timestamp.
  - `Reject`: Records rejection reason in audit log.
- **States:**
  - *No Raw JSON:* Displays only formatted labels, inputs, and confidence pills. Never displays raw OCR payload.
- **API Dependencies:** `GET /api/v1/documents/{id}/review`, `PATCH /api/v1/documents/{id}/fields`, `POST /api/v1/documents/{id}/approve`, `POST /api/v1/documents/{id}/reject`.
- **Destructive Actions:** `Reject` requires entering a written rationale.

---

### Screen 08: Regulatory Change Inbox (`/regulatory-changes`)

- **Objective:** Triage newly published gazette amendments and government notifications.
- **Primary User:** General Counsel, EHS Director.
- **Visual Hierarchy:**
  - Filter pills: All, New (Unreviewed), Under Review, Reviewed, Archived.
  - Change Cards / Table: Notification Number, Issuing Ministry (e.g. MoEFCC), Publication Date, Effective Date, Plain-Language Headline, Impact Rating badge (`High Impact`, `Medium Impact`), Action ("Review Change").
- **API Dependencies:** `GET /api/v1/regulatory-updates`.
- **Destructive Actions:** None.

---

### Screen 09: Regulatory Change Detail & Diff Inspector (`/regulatory-changes/:id`)

- **Objective:** Inspect an official gazette amendment with a side-by-side legal diff, plain-language summary, operative thresholds, and official source link.
- **Primary User:** Plant Manager, Corporate Legal.
- **Visual Hierarchy:**
  - Breadcrumb: `<- Back to Regulatory Changes`.
  - Header: Notification Title ("Amendment to Hazardous Waste Management Rules, 2016") + Badge: "New" + Primary Action: "Mark as Reviewed".
  - Subheader: Ministry name, Notification No. (`S.O. 1234(E)`), Published Date, Effective Date.
  - Tabbed body:
    - *Overview (Active):*
      - Left column: "What changed?", "Key Changes" (bulleted list), "Official Source" (PDF link).
      - Right column: "Who May Be Affected?", "Your Business Impact" callout card.
    - *Impact Assessment:* Deep-dive into plant attributes matched.
    - *Affected Requirements:* Specific register items that need updating.
    - *History:* Audit trail of legal reviews.
- **Main Actions:**
  - `View Notification (PDF)` $\rightarrow$ Opens official government gazette notice in secure viewer.
  - `Review Impact for Your Company` $\rightarrow$ Navigates to Screen 10.
  - `Mark as Reviewed` $\rightarrow$ Records human sign-off.
- **API Dependencies:** `GET /api/v1/regulatory-updates/{id}`, `POST /api/v1/regulatory-updates/{id}/review`.
- **Destructive Actions:** None.

---

### Screen 10: Company Impact Assessment (`/regulatory-changes/:id/impact`)

- **Objective:** Evaluate how an official amendment specifically affects Acme Manufacturing based on operational parameters.
- **Primary User:** Plant Manager, EHS Manager.
- **Visual Hierarchy:**
  - Top alert card: "Deterministic Matching Results - 3 of 4 operational criteria matched".
  - Matched Criteria Table:
    - Criteria (e.g. "Operates in Chemical Sector"): Matched (`Yes`, profile sector: Chemicals)
    - Criteria (e.g. "Stores Category A Waste"): Matched (`Yes`, 18.5 TPA generated)
    - Criteria (e.g. "Located in Maharashtra"): Matched (`Yes`, Pune plant)
  - Missing Facts / Action Plan: Remediation tasks needed (e.g. *"File Form 4 Annual Return with revised Category B code before 30 June"*).
  - Human Decision Controls: "Confirm Applicability to Plant" vs "Declare Inapplicable with Rationale".
- **API Dependencies:** `GET /api/v1/regulatory-updates/{id}/impact/{plant_id}`, `POST /api/v1/regulatory-updates/{id}/review`.
- **Destructive Actions:** Declaring inapplicable requires audit justification.

---

### Screen 11: Tasks & Deadlines (List & Calendar) (`/tasks`)

- **Objective:** Assign, track, and complete compliance remediation actions and permit renewals.
- **Primary User:** All factory compliance staff.
- **Visual Hierarchy:**
  - View toggle: List View vs Calendar View.
  - Status columns: To Do, In Progress, Blocked, Completed.
  - Task Card: Title, Priority Pill (`High`, `Medium`, `Low`), Due Date, Assignee Avatar, Linked Requirement.
- **Main Actions:**
  - Create Task, Edit Task, Mark Completed, Filter by Assignee.
- **API Dependencies:** `GET /api/v1/plants/{id}/tasks`, `POST /api/v1/plants/{id}/tasks`, `PATCH /api/v1/tasks/{id}`.
- **Destructive Actions:** Deleting a task requires confirmation.

---

### Screen 12: Audit & Readiness Report Builder (`/reports/builder`)

- **Objective:** Generate tamper-evident, audit-proof compliance readiness dossiers for board review or state pollution control board inspections.
- **Primary User:** Compliance Auditor, Plant Head.
- **Visual Hierarchy:**
  - Configuration Drawer:
    - Scope: Single Plant or All Plants.
    - Obligation Category: Environmental (MPCB/MoEFCC), Factory Safety (DISH), Boilers, Labour/ESI.
    - Date Range: Active Year, Last Quarter, Custom.
  - Live Preview Pane:
    - Executive Readiness Summary (e.g. 75% Overall Readiness Score).
    - Breakdown table with requirement names, certificate numbers, validity dates, and evidence attachments.
  - Export Options: "Export as Audit PDF", "Export CSV Register".
- **Main Actions:**
  - `Generate Dossier` $\rightarrow$ Downloads structured compliance readiness report.
- **API Dependencies:** `GET /api/v1/plants/{id}/reports/readiness`, `GET /api/v1/plants/{id}/reports/export`.
- **Destructive Actions:** None.

---

### Screen 13: Company Operational Profile & Facts (`/company-profile`)

- **Objective:** Maintain physical factory operational parameters (capacities, chemical inventories, worker headcount) that feed the deterministic applicability engine.
- **Primary User:** Plant Manager, Facility Admin.
- **Visual Hierarchy:**
  - Tabbed categories:
    - *General & Jurisdiction:* Plant name, code, state, district, MIDC industrial zone.
    - *Pollution & Sector:* CPCB Category (Red), Sector (Chemicals), Effluent (KLD), Hazardous waste (TPA).
    - *Equipment Assets:* Boilers, DG Sets, Pressure Vessels, ETP capacity.
    - *Workforce:* Permanent staff, contract labour headcount.
  - "Save Changes & Re-evaluate Applicability" primary button.
- **Main Actions:**
  - Edit operational numbers $\rightarrow$ Prompts that changes will trigger rule re-evaluation.
- **API Dependencies:** `GET /api/v1/plants/{id}/profile`, `PUT /api/v1/plants/{id}/profile`.
- **Destructive Actions:** Modifying operational facts triggers a full register re-evaluation; alert notifies user before saving.

---

### Screen 14: Master Data Administration (`/admin/master-data`)

- **Objective:** Manage standard regulatory authorities, statutory acts, and standard obligation templates.
- **Primary User:** System Administrator (Admin-Only).
- **Visual Hierarchy:**
  - Side navigation: Authorities, Regulatory Acts, Statutory Requirements.
  - CRUD tables with search, edit modal, and status toggles.
- **API Dependencies:** `GET/POST /api/v1/catalog/requirements`.
- **Destructive Actions:** Deleting or modifying a master requirement requires admin password confirmation.

---

### Screen 15: Rule Authoring & Test Bench (`/admin/rules`)

- **Objective:** Author and test deterministic boolean AST rules against sample plant profiles without arbitrary code execution.
- **Primary User:** Regulatory Architect, Senior Legal Counsel.
- **Visual Hierarchy:**
  - Structured Condition Builder: Dropdown operators (`AND`, `OR`, `==`, `>`, `IN`), attribute pickers (`plant.boiler_count`, `plant.jurisdiction`).
  - Test Bench Simulator: Select "Acme Manufacturing (Pune)" $\rightarrow$ Live output shows whether rule evaluates to `PASS` or `FAIL` + interpolated explanation string.
  - Version Comparison & Effective Date picker.
- **Security Rule:** AST is parsed strictly through structured schemas; arbitrary Python or JavaScript evaluation is prohibited.
- **API Dependencies:** `POST /api/v1/admin/rules/simulate`.
- **Destructive Actions:** Deprecating or rolling back a rule version requires admin confirmation.

---

### Screen 16: Users, Roles & Permissions (`/admin/users`)

- **Objective:** Manage enterprise team members, plant access scopes, and RBAC roles.
- **Primary User:** Tenant Administrator.
- **Visual Hierarchy:**
  - User Table: Name, Email, Role (`Plant Manager`, `EHS Manager`, `Admin`, `Auditor`, `Viewer`), Plant Scope, Status, Last Login.
  - "Invite User" button $\rightarrow$ Modal to input email, role, and plant permissions.
- **API Dependencies:** `GET /api/v1/admin/users`, `POST /api/v1/admin/users/invite`.
- **Destructive Actions:** Deactivating or removing a user requires confirmation.

---

### Screen 17: Compliance Intelligence Search (`/search` or `Ctrl+K`)

- **Objective:** Allow factory staff to search requirements, gazette amendments, and uploaded evidence using conversational or keyword queries grounded in verified documents.
- **Primary User:** All Users.
- **Visual Hierarchy:**
  - Global Search Modal (`Ctrl+K` shortcut).
  - Search input with clear button.
  - Categorized results: Requirements (matching permits), Documents (matching certificates), Regulatory Updates (matching gazette notices).
  - For questions: Grounded answer with direct links to verified source PDF clauses; if missing, returns *"Not enough information in active regulations to confirm."*
- **API Dependencies:** `GET /api/v1/search?q=...`.
- **Destructive Actions:** None.

---

### Screen 18: Global Application States

- **Objective:** Guarantee consistent, polished handling of edge cases, errors, and system states across all 17 screens.
- **States Specified:**
  1. **Skeleton Loading:** Shimmering neutral placeholders shaped to match cards, tables, and metric blocks.
  2. **Empty Search / Filter:** Actionable card with *"No matching records found"* + *"Clear Filters"* button.
  3. **First-Run Empty State:** Welcoming illustration + *"Get Started by adding your plant profile"* CTA.
  4. **Permission Denied (HTTP 403):** Muted shield icon + *"You do not have permission to modify this compliance record. Contact your Plant Administrator."*
  5. **Network Offline / Retry:** Persistent amber header banner + *"Connection interrupted. Retrying in 5s... [Retry Now]"*.
  6. **Failed Document Upload:** Red alert banner with specific remediation (e.g. *"File exceeds 20MB limit. Please compress the PDF and try again."*).
