# PlantProof Architecture Reconciliation

**Reviewed repository ref:** `main @ 67aa40caeff9583aa5107eaa5cf81014245fab53`  
**Architecture intent:** preserve the existing modular-monolith implementation while mapping the supplied 7-pillar model and the proposed 10-domain / bounded-context architecture into one hierarchy.

## 1. Reconcile the different architecture counts

The "7 pillars" and the "10 domain groups / 33 bounded contexts" describe different levels of decomposition. They are not inherently conflicting.

- **Pillars** are the top-level enterprise capability map.
- **Domain groups** organize related bounded contexts.
- **Modules** are deployable-code boundaries inside the modular monolith.
- **Entities / aggregates** are owned by those modules; an entity register is not a module count.

Use the 7 pillars as the executive architecture and the 10 groups below as its lower-level implementation map.

## 2. Seven-pillar to ten-domain mapping

| Pillar | Domain group(s) | Scope |
|---|---|---|
| 1. Platform Foundation | Platform Foundation | Tenant, identity, authorization, enterprise organization, tenant configuration, residency and entitlements |
| 2. Shared Reference Taxonomies | Shared Reference Data | Industry/activity, process, equipment, material, units and controlled vocabularies |
| 3. Regulatory Knowledge | Regulatory Knowledge | Jurisdictions, authorities, sources, source artifacts, legal instruments/provisions, obligations, legal review and change intelligence |
| 4. Facility & Context | Facility & Applicability Context | Plant profiles, operations, assets, workforce and typed fact values/provenance |
| 5. Applicability Decisioning | Applicability Decisioning | Rule authoring/versioning and deterministic evaluation with APPLICABLE / NOT_APPLICABLE / UNKNOWN |
| 6. Compliance Operations | Compliance Operations | Plant compliance register, allocation, tasks/remediation, evidence/documents, permits and submissions |
| 7. Cross-Cutting Platform | Workflow & Collaboration; AI & Document Intelligence; Integration & Automation; Platform Operations & Governance | Approvals, notifications, AI governance, connectors, audit/outbox/jobs, analytics, retention/privacy and security operations |

## 3. Existing code modules vs. target bounded contexts

The reviewed repository currently has these 12 backend module packages. They should be evolved, not replaced wholesale:

| Existing package | Primary target context(s) | Direction |
|---|---|---|
| `identity_access` | Identity & Authentication; Authorization & Access Profiles | Split identity/session lifecycle from policy evaluation without breaking current auth APIs |
| `tenant_profile` | Facility Profile & Operations | Keep existing plant API; move facility facts and operational asset lifecycle into clear subdomains |
| `applicability` | Applicability Rule Management; Deterministic Applicability Engine | Separate rule lifecycle from evaluation runtime; preserve three-valued logic |
| `master_data` | Shared Reference Data; Jurisdiction & Authority Registry; parts of legal catalog | Split reference taxonomy from legal instrument/obligation ownership as models mature |
| `requirements` | Obligation Catalog read model; Plant Compliance Register | Separate reusable global obligation from plant-specific compliance instance |
| `documents` | Evidence & Document Management; Document AI & Extraction | Keep file storage/version and evidence review separate from OCR provider implementation |
| `regulatory_intel` | Regulatory Source Registry; Source Ingestion; Legal Review; Regulatory Change Intelligence | Distinguish raw artifact capture from approved legal content |
| `tasks` | Task, Action & Remediation Management | Preserve domain state machine and add explicit task occurrence/recurrence semantics |
| `reminders` | Notifications & Communication; scheduler adapter | Retain package; add durable delivery/job contracts rather than create a duplicate notification module |
| `reports` | Search, Reporting & Analytics | Use read models/projections; reporting must not write operational state |
| `audit` | Audit, Event & Background Job Infrastructure | Keep append-only audit APIs; add transactional outbox/idempotency as platform infrastructure |
| `ai_providers` | AI & Document Intelligence provider adapters | Keep provider abstraction; gate synthetic provider use by environment and evidence status |

## 4. Target bounded contexts

### Platform Foundation
1. Tenant & Tenancy
2. Identity & Authentication
3. Authorization & Access Profiles
4. Organization & Enterprise Structure
5. Tenant Configuration
6. Region & Data Residency
7. Subscription & Entitlements (commercial scale)

### Shared Reference Data
8. Industry & Operational Taxonomy

### Regulatory Knowledge
9. Jurisdiction & Authority Registry
10. Regulatory Source Registry
11. Source Ingestion & Artifact Capture
12. Legal Instrument & Provision Catalog
13. Obligation Catalog
14. Legal Review & Source Verification
15. Regulatory Change Intelligence

### Facility & Applicability Context
16. Facility Profile & Operations
17. Facility Facts & Evidence Inputs

### Applicability Decisioning
18. Applicability Rule Management
19. Deterministic Applicability Engine

### Compliance Operations
20. Plant Compliance Register
21. Compliance Allocation & Responsibility
22. Task, Action & Remediation Management
23. Evidence & Document Management
24. Permits, Licenses & Submissions

### Cross-Cutting Platform
25. Workflow & Approval Orchestration
26. Notifications & Communication
27. Document AI & Extraction
28. AI Governance & Knowledge Assistance
29. Integration Gateway & Connectors
30. Audit, Event & Background Job Infrastructure
31. Search, Reporting & Analytics
32. Data Governance, Retention & Privacy
33. Security & Service Operations

This target context list is a logical map, not an instruction to create 33 separate Python packages immediately. Keep the current 12 packages where cohesive; split only when ownership, lifecycle or change cadence requires a boundary.

## 5. Core aggregate ownership rules

| Aggregate / data | Owning context | Notes |
|---|---|---|
| Tenant, TenantVersion, TenantLifecycleEvent | Tenant & Tenancy | Tenant is SaaS isolation boundary, not legal entity/plant |
| User, Authenticator, Session, ExternalIdentity | Identity & Authentication | Global user identity; no tenant-specific role as identity property |
| TenantMembership, AccessProfileVersion, ScopeGrant | Authorization / Tenant membership | Tenant-specific memberships and grants |
| OrgNode, LegalEntity, Plant, Facility | Organization & Enterprise Structure | Separate organizational hierarchy from jurisdiction |
| SettingDefinition, TenantSettingVersion | Tenant Configuration | Stable setting identity + immutable value revisions |
| RegulatorySource, SourceArtifact | Source Registry / Ingestion | Store retrieval provenance and original artifact checksum |
| LegalInstrumentVersion, LegalProvisionVersion | Legal Catalog | Versioned legal text with exact source links |
| RegulatoryObligation, ObligationVersion | Obligation Catalog | Global/curated legal requirement |
| FacilityFactVersion | Facility Facts | Tenant-owned, typed, effective-dated fact with source and validation |
| ApplicabilityRuleVersion | Rule Management | Immutable published rule version |
| EvaluationRun, Decision, ConditionResult | Applicability Engine | Preserve exact fact/rule/engine input and output |
| PlantComplianceInstance | Plant Compliance Register | Central plant-specific operational compliance record |
| ComplianceAssignment | Allocation | Responsibility and scope grant trace |
| TaskOccurrence, TaskStatusEvent | Task Management | Recurrence is distinct from reusable task definition |
| Document, DocumentVersion, StoredObject | Document Management | Blob object lifecycle separated from evidence claim |
| EvidenceRecord, EvidenceReview | Evidence Management | Evidence claim and review lifecycle |
| WorkflowInstance, ApprovalDecision | Workflow | Workflow coordinates, owning domain commits state |
| AuditEvent, OutboxEvent, IdempotencyRecord | Platform Operations | Shared cross-cutting infrastructure |

## 6. Non-negotiable architectural boundaries

1. **Tenant vs legal entity vs plant:** tenant is the SaaS security/commercial boundary; legal entity and plant live in organization hierarchy.
2. **User vs membership vs grant:** global identity is separate from tenant membership and scoped permissions.
3. **Legal source vs obligation vs applicability rule:** raw source, normalized obligation and deterministic operational logic are distinct.
4. **Obligation vs decision vs compliance instance:** reusable requirement, plant evaluation and tenant operational record are three separate concepts.
5. **Task vs evidence vs document:** task is work; evidence is a reviewed claim; document is a file/version.
6. **Workflow vs domain state:** workflow orchestrates review; owning domain enforces and persists the approved transition.
7. **AI vs legal authority:** AI drafts proposals; authorized human review verifies; deterministic engine evaluates published rule versions.
8. **Audit vs version vs backup:** immutable domain history, append-only audit and infrastructure durability are separate controls.

## 7. Dependency direction

- Regulatory catalog is not owned by customer tenants; plant facts and operational compliance records are tenant-owned.
- Applicability consumes verified obligation/rule versions and tenant fact snapshots.
- Compliance register consumes applicability decisions; tasks consume compliance instances and approved assignments.
- Evidence services own documents/evidence; tasks and facts reference evidence through explicit association records.
- Workflow calls domain commands after approval; it does not directly mutate another module's ORM objects.
- Reporting consumes events/read models and is never the system-of-record write path.
- Shared infrastructure (audit, outbox, idempotency, job runtime) is accessed through stable interfaces.
- Avoid generic polymorphic `entity_type/entity_id` as the only relationship mechanism for operational records; use typed foreign keys and explicit association entities.

## 8. Recommended implementation sequence

1. Reconcile the exact latest working tree with GitHub and freeze a baseline commit.
2. Harden Tenant, Identity, Membership, Organization and Authorization as one foundation workstream.
3. Establish lifecycle/versioning, tenant ownership and audit/outbox foundations before expanding entities.
4. Correct legal provenance and 3-valued applicability before adding more regulatory coverage.
5. Build facility facts and applicability decisions as versioned inputs/outputs.
6. Reconcile compliance register, allocation, task occurrences and evidence without duplicating existing modules.
7. Add durable jobs, delivery providers, storage, residency and retention controls.
8. Add CI/CD, staging deployment, database restore tests, load/security tests and release runbooks.

Do not freeze a detailed ERD until aggregate ownership, cardinality, tenant ownership and deletion/retention behavior have been decided for that domain.
