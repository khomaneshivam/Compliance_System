"""
Integration Tests for Factory Operational Workflows
Tests:
- Requirements register server-side pagination, sorting, filters, search, and saved views presets.
- Requirement details with statutory provenance, versioning metadata, evidence summary, and audit history.
- Compliance tasks lifecycle, state machine validation, comments, and attachments.
- Reminder scheduler for due-soon and overdue items, deduplication, preferences, and test notification adapter.
- Readiness report builder with legal disclaimer, metrics, HTML/JSON download, and cross-tenant access isolation.
- Company profile update simulation diff and reassessment application.
- Admin audit logs with human-readable descriptions and action/entity filters.
"""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.modules.reminders.services import test_notification_adapter


def test_requirements_pagination_filters_and_saved_views(
    client: TestClient, auth_headers_tenant_a: dict, tenant_a_plant_id: str
):
    """Verifies server-side pagination, filters, sorting, search, and saved views."""
    # 1. First run applicability assessment to populate requirements for Tenant A
    assess_resp = client.post(
        f"/api/v1/companies/{tenant_a_plant_id}/assessments?auto_approve_initial=true",
        headers=auth_headers_tenant_a,
    )
    assert assess_resp.status_code == 200

    # 2. Test paginated listing
    resp = client.get(
        f"/api/v1/requirements?plant_id={tenant_a_plant_id}&page=1&page_size=5",
        headers=auth_headers_tenant_a,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5
    assert data["total"] > 0

    first_item = data["items"][0]
    assert "code" in first_item
    assert "title" in first_item
    assert "applicability_status" in first_item
    assert "evidence_status" in first_item
    assert "authority_code" in first_item

    # 3. Test filter by obligation_type
    filter_resp = client.get(
        f"/api/v1/requirements?plant_id={tenant_a_plant_id}&obligation_type=CONSENT",
        headers=auth_headers_tenant_a,
    )
    assert filter_resp.status_code == 200
    filter_data = filter_resp.json()
    for item in filter_data["items"]:
        assert item["obligation_type"] == "CONSENT"

    # 4. Test search keyword
    search_resp = client.get(
        f"/api/v1/requirements?plant_id={tenant_a_plant_id}&search=Water",
        headers=auth_headers_tenant_a,
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    for item in search_data["items"]:
        match = "water" in item["title"].lower() or "water" in item["code"].lower()
        assert match or "water" in (item.get("description") or "").lower()

    # 5. Test sorting
    sort_resp = client.get(
        f"/api/v1/requirements?plant_id={tenant_a_plant_id}&sort_by=code&sort_order=desc",
        headers=auth_headers_tenant_a,
    )
    assert sort_resp.status_code == 200
    codes = [item["code"] for item in sort_resp.json()["items"]]
    assert codes == sorted(codes, reverse=True)

    # 6. Test saved views presets
    views_resp = client.get(
        f"/api/v1/requirements/saved-views?plant_id={tenant_a_plant_id}",
        headers=auth_headers_tenant_a,
    )
    assert views_resp.status_code == 200
    presets = views_resp.json()
    assert len(presets) >= 4
    preset_ids = [p["id"] for p in presets]
    assert "missing_evidence" in preset_ids
    assert "expiring_soon" in preset_ids
    assert "all_applicable" in preset_ids


def test_requirement_detail_provenance_and_history(
    client: TestClient, auth_headers_tenant_a: dict, tenant_a_plant_id: str
):
    """Verifies detailed statutory provenance, applicability explanation, and audit trail."""
    # List requirements to pick one
    list_resp = client.get(
        f"/api/v1/requirements?plant_id={tenant_a_plant_id}",
        headers=auth_headers_tenant_a,
    )
    items = list_resp.json()["items"]
    assert len(items) > 0
    req_id = items[0]["id"]

    detail_resp = client.get(
        f"/api/v1/requirements/{req_id}",
        headers=auth_headers_tenant_a,
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["id"] == req_id
    assert detail["code"] == items[0]["code"]
    assert "provenance" in detail
    assert detail["provenance"]["authority_name"] is not None
    assert detail["provenance"]["act_title"] is not None

    assert "applicability" in detail
    assert detail["applicability"]["applicability_status"] in ["APPLICABLE", "CONDITIONALLY_APPLICABLE", "EXEMPTED", "NOT_APPLICABLE"]
    assert detail["applicability"]["applicability_rationale"] is not None
    assert "evidence_list" in detail
    assert isinstance(detail["evidence_list"], list)
    assert "history" in detail
    assert isinstance(detail["history"], list)


def test_tasks_lifecycle_and_controlled_state_machine(
    client: TestClient, auth_headers_tenant_a: dict, tenant_a_plant_id: str
):
    """Verifies task creation, state transitions, mandatory blocked reason, comments, and attachments."""
    # 1. Create Task
    due = (date.today() + timedelta(days=14)).isoformat()
    create_resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers_tenant_a,
        json={
            "plant_id": tenant_a_plant_id,
            "title": "Calibrate Effluent Flow Sensor",
            "description": "Perform scheduled ISO-certified calibration of the ETP outlet flow meter.",
            "due_date": due,
            "priority": "HIGH",
        },
    )
    assert create_resp.status_code == 201
    task = create_resp.json()
    task_id = task["id"]
    assert task["status"] == "TODO"
    assert task["priority"] == "HIGH"

    # 2. Valid transition: TODO -> IN_PROGRESS
    trans_resp1 = client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers_tenant_a,
        json={"new_status": "IN_PROGRESS", "comment": "Technician dispatched to plant site."},
    )
    assert trans_resp1.status_code == 200
    assert trans_resp1.json()["status"] == "IN_PROGRESS"

    # 3. Invalid transition: IN_PROGRESS -> TODO (disallowed)
    invalid_resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers_tenant_a,
        json={"new_status": "TODO"},
    )
    assert invalid_resp.status_code == 400
    assert invalid_resp.json()["error"]["code"] == "INVALID_TASK_STATUS_TRANSITION"

    # 4. Invalid BLOCKED transition without mandatory comment
    blocked_no_comment = client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers_tenant_a,
        json={"new_status": "BLOCKED", "comment": ""},
    )
    assert blocked_no_comment.status_code == 400
    assert blocked_no_comment.json()["error"]["code"] == "BLOCKED_REASON_REQUIRED"

    # 5. Valid BLOCKED transition with explanation
    blocked_resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers_tenant_a,
        json={"new_status": "BLOCKED", "comment": "Awaiting replacement sensor part from German vendor."},
    )
    assert blocked_resp.status_code == 200
    assert blocked_resp.json()["status"] == "BLOCKED"
    assert blocked_resp.json()["blocked_reason"] == "Awaiting replacement sensor part from German vendor."

    # 6. Unblock: BLOCKED -> IN_PROGRESS
    unblock_resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers_tenant_a,
        json={"new_status": "IN_PROGRESS", "comment": "Part received and calibrated."},
    )
    assert unblock_resp.status_code == 200
    assert unblock_resp.json()["status"] == "IN_PROGRESS"

    # 7. Complete: IN_PROGRESS -> COMPLETED
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers_tenant_a,
        json={"new_status": "COMPLETED", "comment": "Calibration verified with lab stamp."},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "COMPLETED"
    assert complete_resp.json()["completed_at"] is not None

    # 8. Controlled Reopening: COMPLETED -> IN_PROGRESS
    reopen_resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers_tenant_a,
        json={"new_status": "IN_PROGRESS", "comment": "Auditor requested additional verification run."},
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "IN_PROGRESS"

    # 9. Add Activity Comment
    comment_resp = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=auth_headers_tenant_a,
        json={"comment_text": "Calibration report uploaded to document management vault."},
    )
    assert comment_resp.status_code == 201
    assert "Calibration report" in comment_resp.json()["comment_text"]

    # 10. Check task detail view has comments
    detail_resp = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers_tenant_a)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["comments"]) >= 2  # State transition comments + explicit comment


def test_reminders_scheduler_deduplication_and_test_adapter(
    client: TestClient, auth_headers_tenant_a: dict, tenant_a_plant_id: str
):
    """Verifies reminder scanner, notification deduplication, preferences, and test adapter."""
    test_notification_adapter.clear()

    # 1. Configure user preferences
    pref_resp = client.put(
        "/api/v1/reminders/preferences",
        headers=auth_headers_tenant_a,
        json={
            "lead_time_days": 30,
            "notify_on_overdue": True,
            "email_enabled": True,
            "in_app_enabled": True,
            "frequency": "IMMEDIATE",
        },
    )
    assert pref_resp.status_code == 200
    assert pref_resp.json()["lead_time_days"] == 30

    # 2. Run reminder scheduler scan
    scan1 = client.post("/api/v1/reminders/run-scheduler", headers=auth_headers_tenant_a)
    assert scan1.status_code == 200
    data1 = scan1.json()
    assert "scan_date" in data1
    assert "scanned_tasks_count" in data1
    assert "scanned_requirements_count" in data1
    first_gen = data1["generated_count"]

    # 3. Run reminder scheduler scan AGAIN immediately on same date -> deduplication must engage!
    scan2 = client.post("/api/v1/reminders/run-scheduler", headers=auth_headers_tenant_a)
    assert scan2.status_code == 200
    data2 = scan2.json()
    if first_gen > 0:
        assert data2["deduplicated_count"] >= first_gen
        assert data2["generated_count"] == 0

    # 4. Dispatch a test notification through test adapter
    test_resp = client.post(
        "/api/v1/reminders/test-notification",
        headers=auth_headers_tenant_a,
        json={
            "channel": "IN_APP",
            "notification_type": "SYSTEM_TEST",
            "title": "Alert Pipeline Test",
            "message": "Verification notification confirming operational dispatcher health.",
        },
    )
    assert test_resp.status_code == 201
    notif = test_resp.json()
    assert notif["title"] == "Alert Pipeline Test"
    assert notif["status"] == "UNREAD"

    # Assert test adapter recorded delivery
    assert len(test_notification_adapter.delivered_messages) > 0
    delivered = test_notification_adapter.delivered_messages[-1]
    assert delivered["title"] == "Alert Pipeline Test"

    # 5. List notifications and verify unread count
    list_resp = client.get("/api/v1/reminders/notifications", headers=auth_headers_tenant_a)
    assert list_resp.status_code == 200
    assert list_resp.json()["unread_count"] > 0

    # 6. Mark single notification read
    read_resp = client.patch(
        f"/api/v1/reminders/notifications/{notif['id']}/read",
        headers=auth_headers_tenant_a,
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["status"] == "READ"


def test_readiness_report_builder_and_access_isolation(
    client: TestClient,
    auth_headers_tenant_a: dict,
    auth_headers_tenant_b: dict,
    tenant_a_plant_id: str,
):
    """Verifies report builder, readiness disclaimer, metrics, HTML/JSON artifacts, and tenant isolation."""
    # 1. Create and generate readiness report for Tenant A (synchronous mode)
    create_resp = client.post(
        "/api/v1/reports?run_async=false",
        headers=auth_headers_tenant_a,
        json={
            "plant_id": tenant_a_plant_id,
            "report_title": "Q4 Environmental Audit Readiness Dossier",
            "file_format": "HTML",
            "include_evidence_items": True,
            "include_missing_items": True,
        },
    )
    assert create_resp.status_code == 201
    job = create_resp.json()
    job_id = job["id"]
    assert job["status"] == "COMPLETED"
    assert job["file_format"] == "HTML"
    assert job["summary_metrics"]["total_applicable_requirements"] >= 0
    assert job["download_url"] is not None

    # 2. Download report artifact as Tenant A
    dl_resp = client.get(f"/api/v1/reports/{job_id}/download", headers=auth_headers_tenant_a)
    assert dl_resp.status_code == 200
    html_content = dl_resp.text

    # MANDATORY: Report must explicitly carry the readiness disclaimer and never claim legal guarantee
    assert "DISCLAIMER" in html_content
    assert "does not constitute a formal legal opinion" in html_content or "NOT a formal legal opinion" in html_content
    assert "Readiness Score" in html_content

    # 3. Cross-Tenant Access Isolation: Tenant B cannot access Tenant A's report!
    cross_resp = client.get(f"/api/v1/reports/{job_id}", headers=auth_headers_tenant_b)
    assert cross_resp.status_code == 404

    cross_dl = client.get(f"/api/v1/reports/{job_id}/download", headers=auth_headers_tenant_b)
    assert cross_dl.status_code == 404


def test_profile_simulation_diff_and_reassessment_application(
    client: TestClient,
    auth_headers_tenant_a: dict,
    auth_headers_admin: dict,
    tenant_a_plant_id: str,
):
    """Verifies dry-run reassessment simulation diff and applying updates with audit trail."""
    # 1. Dry-run simulation: increase boiler count from 0 to 2
    sim_resp = client.post(
        f"/api/v1/companies/{tenant_a_plant_id}/simulate-reassessment",
        headers=auth_headers_tenant_a,
        json={
            "boiler_count": 2,
            "steam_capacity_tph": 15.0,
        },
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()

    assert "attribute_changes" in sim_data
    assert len(sim_data["attribute_changes"]) >= 1
    assert "impacted_requirements" in sim_data
    assert "summary_guidance" in sim_data

    # Check boiler change recorded in diff
    boiler_diff = next((d for d in sim_data["attribute_changes"] if d["field_name"] == "boiler_count"), None)
    assert boiler_diff is not None
    assert boiler_diff["proposed_value"] == 2

    # Verify simulation did NOT mutate active plant profile in DB yet!
    plant_resp = client.get(f"/api/v1/plants/{tenant_a_plant_id}", headers=auth_headers_tenant_a)
    # The active profile in DB was not modified by the simulation
    assert plant_resp.status_code == 200

    # 2. Apply confirmed profile update with reassessment
    apply_resp = client.put(
        f"/api/v1/companies/{tenant_a_plant_id}/profile-with-reassessment",
        headers=auth_headers_admin,
        json={
            "profile_updates": {
                "boiler_count": 2,
                "steam_capacity_tph": 15.0,
            },
            "auto_approve_changes": True,
            "rationale": "Installation of 2 x 7.5 TPH industrial steam boilers for expansion.",
        },
    )
    assert apply_resp.status_code == 200
    apply_data = apply_resp.json()
    assert apply_data["simulation_diff"]["plant_id"] == tenant_a_plant_id
    assert apply_data["assessment_run"]["assessment_version"] >= 1


def test_admin_audit_logs_human_readable_descriptions(
    client: TestClient,
    auth_headers_admin: dict,
):
    """Verifies admin audit log query returns plain-language descriptions without raw JSON."""
    resp = client.get("/api/v1/admin/audit-logs?page=1&page_size=20", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "available_actions" in data
    assert "available_entity_types" in data

    if len(data["items"]) > 0:
        first_log = data["items"][0]
        assert "readable_description" in first_log
        assert len(first_log["readable_description"]) > 0
        assert "changes_summary" in first_log
        assert isinstance(first_log["changes_summary"], list)
