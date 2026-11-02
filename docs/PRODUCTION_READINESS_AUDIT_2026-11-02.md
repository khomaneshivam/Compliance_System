# PlantProof Production Readiness Audit

**Audit date:** 2026-11-02  
**Repository:** `khomaneshivam/Compliance_System`  
**Reviewed ref:** `main` at `67aa40caeff9583aa5107eaa5cf81014245fab53`  
**Audit type:** Static source and repository-structure review. This is not a penetration test, runtime validation, or production certification.

## Executive assessment

The current repository is a substantial local-evaluation modular monolith, but the accessible `main` branch is **not production-ready**. It contains functional regulatory, applicability, task, evidence and reporting modules, plus useful security controls. Several core data and legal-provenance boundaries remain insufficient for a defensible enterprise compliance platform.

No application code was changed as part of this audit. A dedicated branch contains this audit and the architecture reconciliation document. Runtime tests were not executed from the GitHub connector; do not interpret historic test counts in project documentation as a fresh verification.

## 1. Verified repository baseline

The GitHub tree at the reviewed commit contains:
- 12 backend module directories under `app/modules/`.
- 7 Alembic migration files under `alembic/versions/`.
- 251 tracked file blobs in the recursive tree.
- One branch visible to the connected account: `main`.
- No `.github/workflows/` files in the tree and zero GitHub Actions workflow runs returned by the Actions endpoint.
- The README explicitly says cloud production deployment (AWS/GCP infrastructure, Kubernetes, Terraform, CDN and TLS provisioning) is outside the current implementation scope.

The existing backend modules are `ai_providers`, `applicability`, `audit`, `documents`, `identity_access`, `master_data`, `regulatory_intel`, `reminders`, `reports`, `requirements`, `tasks` and `tenant_profile`.

## 2. Important synchronization discrepancy

The separately supplied PlantProof implementation note describes changes that are **not present in the reviewed GitHub `main` tree**, including:
- `app/core/zero_data_loss.py` and a global SQLAlchemy delete interceptor.
- Alembic revisions `7b1e4c9f2a01` and `8c2d5e1a3b02`.
- A `modules/execution_flow/` package and related endpoints.
- Expanded tenant membership/version/residency entities and a 55-table model count.
- A 164-test result and a MySQL schema shift script.

The accessible `main` tree instead ends at commit `67aa40c`, contains seven migration files and has no `execution_flow` or `zero_data_loss.py` path. Those newer changes may exist in a local working tree or an unpushed branch, but they cannot be treated as code on this GitHub ref. Before porting or duplicating them, synchronize the intended latest source branch to GitHub.

## 3. Findings from active source code

### P0 — Tenant data can be hard-deleted through ORM cascades

Evidence:
- `app/models/tenancy.py`: `Tenant.users` and `Tenant.plants` are configured with `cascade="all, delete-orphan"`.
- The `User` and `Plant` foreign keys reference `tenants.id` with `ondelete="CASCADE"`.
- `Plant.profile`, `Plant.equipment` and `Plant.requirements` also use delete cascades / delete-orphan relationships.
- Other operational models also contain `ondelete="CASCADE"` and delete-orphan child relationships.
- The reviewed tree has no `app/core/zero_data_loss.py` and `app/core/database.py` has no registered global delete interceptor.

Impact: deleting a tenant, plant, task, document or parent object through a relationship or database cascade can erase dependent operational and evidence records. This conflicts with the supplied append-only data policy.

Required remediation:
1. Define the lifecycle model before applying a global interceptor.
2. Remove destructive ORM cascades and change retained-history foreign keys to restrictive behavior where appropriate.
3. Replace business delete operations with typed deactivation, archival, revocation or superseding commands.
4. Protect immutable version/event/audit tables from UPDATE/DELETE using database privileges and, where supported, database triggers. A SQLAlchemy `before_flush` hook alone does not catch Core bulk DML, raw SQL, database-side cascades or privileged database users.
5. Keep physical erasure as a separately authorized retention/privacy operation with legal-hold checks, execution evidence and audit. Do not retain every class of personal data indefinitely without a lawful retention basis.
6. Test ORM deletion, bulk ORM deletion, Core DELETE, raw SQL, cascades, migration behavior and restoration independently.

### P0 — User invitations provision a shared known password

Evidence: `app/modules/identity_access/router.py`, `invite_user` creates an active user with `get_password_hash("Password123!")`.

Impact: every invited user is created with the same publicly guessable initial credential and is immediately active. The role gate and SUPER_ADMIN escalation check are positive controls, but they do not solve credential bootstrapping.

Required remediation: implement a one-time invitation flow using a cryptographically random token, store only its hash, bind it to the intended email and tenant, set an expiry and single-use state, deliver it through a configured channel, and require the recipient to set their own password before activation. Do not return or log invite tokens.

### P0 — Tenant identity, membership and authorization are not yet the agreed future model

Evidence: `app/models/tenancy.py` stores `tenant_id` and a single `role` directly on `User`. There is no `TenantMembership`, `TenantMembershipVersion`, versioned access-profile assignment or scope-grant model in the reviewed model tree. `get_current_user` resolves one user and its single tenant; `require_roles` implements coarse role checks.

Impact: one global user identity cannot safely participate in multiple tenants with distinct roles and scopes. This is not sufficient for the planned enterprise hierarchy and scoped RBAC/ABAC model.

Required remediation: design a backward-compatible identity migration: global user identity, tenant memberships with lifecycle history, versioned access profiles, scoped grants and explicit authorization policy evaluation. Preserve existing user IDs and role meaning during migration; use an expand/backfill/validate/contract sequence.

### P1 — Requirement detail can fabricate legal provenance

Evidence: `app/modules/requirements/services.py` constructs fallback clause references such as `Section 25/26` or `Section 7/8`, a `Gazette Notification Pending` reference and regulator URLs inferred from an authority code.

Impact: a UI/API response can display plausible but unverified statutory citations or URLs as if they were actual source provenance.

Required remediation: return null/unknown/unverified fields when source data is absent. Display a clear missing-provenance state. A URL, section, Gazette number or date must originate from a captured and reviewed source record.

### P1 — Rule approval can silently mark a source verified

Evidence: `app/modules/applicability/services.py`, `approve_rule`, changes `source_verification_status` from `PROPOSED` or `UNVERIFIED_DEMO` to `VERIFIED` during rule approval.

Impact: approval of applicability logic is conflated with verification that the cited legal source is authentic and correctly interpreted.

Required remediation: separate source verification from rule approval. Require independently recorded source-verification evidence and an authorized reviewer. Rule approval must preserve the original source-verification state.

### P1 — Missing facility facts can be presented as numeric zero

Evidence: `app/modules/requirements/services.py` falls back to values such as `effluent_discharge_kld or 0.0`, `connected_power_kw or 0.0` and `steam_capacity_tph or 0.0` when reconstructing applicability facts.

Impact: unknown or absent measurements can be misrepresented as confirmed zero. This can support a false `NOT_APPLICABLE` explanation.

Required remediation: preserve null/unknown distinctly from measured zero, identify missing facts in the response and preserve the exact evaluation input snapshot.

### P1 — Synthetic document extraction is wired as the default provider

Evidence: `app/modules/documents/ai_service.py` ends with `ai_extractor_provider = MockSyntheticDocumentAIProvider()`. The provider contains hardcoded sample dates, authority names, values, confidence scores and fallback expiry dates. `app/modules/documents/pipeline.py` uses this provider.

Impact: synthetic fixture output can look like a real extraction result. In a compliance-evidence product, fabricated dates, certificate fields or confidence scores must never be eligible for verified evidence.

Required remediation: make provider mode explicit and environment-gated. In production, require a configured real provider or return `PROVIDER_NOT_CONFIGURED`; never create synthetic legal values. Mark fixture output as non-evidence in the database/API/UI and prevent it from being approved as real evidence.

### P1 — Applicability type mismatch can resolve to FALSE

Evidence: `app/modules/applicability/engine.py` contains a type-comparison exception path that returns `False` on `ValueError` / `TypeError`.

Impact: invalid or incompatible data may become a negative applicability result instead of `UNKNOWN` / needs-review. This violates the required three-valued logic.

Required remediation: return an explicit UNKNOWN result with a structured evaluation error and missing/invalid fact list. Add tests for incompatible types, absent values, malformed AST values and nested Kleene logic.

### P1 — Notification ownership check is tenant-scoped, not recipient-scoped

Evidence: `app/modules/reminders/services.py`, `mark_as_read`, checks `notif.tenant_id == user.tenant_id` but does not require `notif.user_id == user.id` or a shared-tenant notification with `user_id IS NULL`.

Impact: a user can mutate another user's personal notification inside the same tenant.

Required remediation: enforce recipient ownership or the documented shared-notification rule in the database query itself. Add same-tenant cross-user negative tests.

### P1 — Reminder deduplication is race-prone

Evidence: `app/modules/reminders/services.py` performs a read-before-insert check on a unique deduplication key. Concurrent scheduler runs can both observe no row and then race on insert.

Impact: one request may raise an unhandled uniqueness/IntegrityError rather than returning an idempotent outcome.

Required remediation: use database-native conflict handling or a unique-key insert strategy, make scheduler execution idempotent and record generated/skipped/failed counts.

### P1 — Reminder scheduling and delivery are not durable background operations

Evidence: the current reminder router exposes an on-demand scheduler endpoint. The codebase has no durable worker/queue implementation or GitHub-managed deployment configuration in the reviewed tree. The existing rate limiter is process-local.

Impact: scheduled reminders and retries are not guaranteed across process restarts or multiple application instances.

Required remediation: introduce a worker abstraction and durable job/outbox store; retain an in-memory adapter only for tests/local mode. Add retry/backoff, lease/heartbeat, dead-letter handling and delivery-state separation.

### P1 — Existing facility profile auto-creation uses synthetic operational values

Evidence: `app/modules/tenant_profile/services.py`, `get_or_create_plant_profile`, inserts fixed example values (employee count, capacities, hazardous waste, effluent, boilers and sector) when no profile exists.

Impact: a real plant with no profile can receive invented operational facts that affect applicability.

Required remediation: create an explicitly incomplete profile with null/unknown facts and an onboarding status. Seed synthetic operational profiles only from a development/test fixture command.

## 4. Positive controls already present on reviewed main

The following should be preserved rather than rewritten:
- `app/core/config.py` validates production/staging configuration: rejects DEBUG, known placeholder/weak signing secrets and demo-user seeding.
- `app/main.py` uses `Base.metadata.create_all()` only in development/test when explicitly enabled; staging/production relies on Alembic and checks database connectivity.
- Demo fixtures are gated to development/test; production/staging seed failures fail startup.
- Role checks exist on user invitation and several sensitive endpoints.
- Security headers, correlation ID validation, structured logging and file-vault path safeguards exist in the current code.

Older gap-audit documents in the repository contain statements that are no longer true in the reviewed source (for example, startup always calling `create_all` and unconditionally seeding demo users). Re-audit source before acting on historical audit claims.

## 5. Deployment and verification gaps

- No GitHub Actions workflow files were found and the repository Actions endpoint returned zero workflow runs. CI/CD is therefore not demonstrated on the connected repository.
- The README explicitly identifies cloud production deployment as out of scope. No verified infrastructure-as-code / production deployment baseline was found in the root tree.
- Local filesystem vault storage is used; production object storage, encryption/key management, backup/restore and disaster-recovery behavior are not established by this static review.
- The repository has test files and local audit documents, but this review did not execute tests or builds. Previous test counts in README, uploaded notes and audit documents differ and refer to different snapshots. Record test results only against a commit SHA and actual CI run.

## 6. Zero-data-loss policy clarification

The engineering objective should be **historical integrity and controlled lifecycle**, not an unconditional promise that every record and every personal datum is retained forever.

- Business changes create new immutable versions or append lifecycle events.
- Audit, legal source artifacts, approved rule versions and evidence provenance are protected against ordinary mutation.
- Deactivation/archive is the normal business lifecycle operation.
- Physical purge is a separate, authorized process for records that have reached retention limits or must be erased under applicable privacy/contract/legal requirements.
- Database durability is a separate control: define RPO/RTO, backups, WAL/PITR, replication/failover and tested restores. ORM versioning does not provide infrastructure-level zero data loss.

A SQLAlchemy flush interceptor is useful defense in depth but cannot alone guarantee no hard deletes across ORM bulk DML, Core SQL, raw SQL, foreign-key cascades or database administrators.

## 7. Prioritized implementation sequence

1. **Synchronize the real baseline:** push or identify the local/unpublished zero-data-loss and taxonomy/execution-flow changes described in the supplied implementation note. Re-run the audit against that exact commit.
2. **P0 identity and tenant safety:** invitation-token activation; tenant membership model; tenant-aware ownership; replace destructive cascades with controlled lifecycle; establish database-level immutability for the correct tables.
3. **P0 regulatory integrity:** remove fabricated legal references; separate source verification from rule approval; preserve UNKNOWN facts and evaluation semantics; remove synthetic operational facts.
4. **P1 evidence integrity:** gate fixture AI providers; add explicit provider mode and production fail-closed behavior; preserve extraction runs and reviewer decisions as history.
5. **P1 notifications/jobs:** recipient scoping, concurrency-safe deduplication, durable scheduler/worker/outbox, delivery state and retries.
6. **P1/P2 operations:** distributed rate limiting, object storage, encryption/key management, backup/PITR, observability, deployment automation and restore drills.
7. **Release verification:** add CI, run migrations from empty and populated databases, test rollback/restore and cross-tenant negative cases, execute backend/frontend/security/load suites, and publish evidence for the exact release commit.

## 8. Acceptance gates for production claims

Do not describe PlantProof as production-ready until:
- Tenant isolation is tested across every tenant-owned API, job, report, document and event consumer.
- Invitation/password/session lifecycle is secure and revocable.
- Legal provenance cannot be fabricated and source verification is distinct from business approval.
- Applicability uses three-valued logic and stores immutable inputs/outputs.
- Synthetic providers cannot generate approved customer evidence in production.
- Business deletes cannot cascade through retained evidence or audit records.
- Retention/purge/legal-hold workflows are governed and tested.
- Background jobs are durable and idempotent across restarts/multiple replicas.
- PostgreSQL migrations, backups, restore, failover and RPO/RTO have been tested.
- CI and deployment pipelines have real passing runs, not only local documentation.

---
This report is a code-grounded engineering baseline, not a legal opinion, certification or independent penetration-test report.
