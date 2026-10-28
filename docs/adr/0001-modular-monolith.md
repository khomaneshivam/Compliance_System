# ADR 0001: Adoption of Modular Monolith Architecture

## Status
**Accepted**

## Context
PlantProof is an enterprise multi-tenant compliance intelligence and evidence management platform. The domain involves interrelated capabilities: multi-tenant plant profile management, statutory catalog management, deterministic applicability evaluation, document OCR and validation, regulatory intelligence change tracking, remediation task management, and audit reporting.

During initial system design, architectural choices were evaluated:
1. Microservices Architecture
2. Traditional Layered Monolith (untethered)
3. Modular Monolith

## Decision
We adopt a **Modular Monolith** architecture implemented as a single deployable Python FastAPI application backed by a PostgreSQL database, paired with a React 18 + Vite + TypeScript frontend.

Key constraints of this architecture:
- Each domain module (`identity_access`, `tenant_profile`, `master_data`, `rule_versioning`, `applicability`, `document_evidence`, `regulatory_sources`, `tasks_notifications`, `audit_reporting`, `admin_review`) is isolated inside `app/modules/`.
- Modules communicate strictly through typed service interfaces and DTOs.
- Direct cross-module imports of database entity models are prohibited to avoid circular dependencies.
- A single relational database transaction spans multi-step operations (e.g. document approval updating both the evidence record and the linked requirement status).

## Consequences
### Positive
- High developer velocity and simplified local testing without distributed tracing or multi-container networking.
- ACID transactions guarantee compliance state consistency without distributed two-phase commits.
- Clear module boundaries allow extracting specific modules (e.g. OCR processing or regulatory scrapers) into microservices in the future if throughput necessitates it.

### Negative / Trade-offs
- Deployment updates the entire monolith rather than individual sub-domains.
- Discipline is required to prevent accidental boundary leaks (enforced through automated architecture linting and code reviews).
