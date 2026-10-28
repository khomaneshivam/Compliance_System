"""
Unit Tests for PlantProof Reminders, Multi-Channel Delivery Adapters, Document & Regulatory Scanning
"""

from datetime import date, timedelta, datetime, timezone
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.models.tenancy import Tenant, Plant, User
from app.models.tasks import ComplianceTask
from app.models.requirements import PlantRequirement
from app.models.catalog import StatutoryRequirement, RegulatoryAuthority, RegulatoryAct
from app.models.documents import ComplianceDocument
from app.models.assessments import ProposedRequirementChange
from app.models.reminders import ReminderNotification, UserNotificationPreference
from app.modules.reminders.services import (
    ReminderService,
    NotificationAdapter,
    TestNotificationAdapter,
    ConsoleNotificationAdapter,
    SmtpNotificationAdapter,
    get_notification_adapter,
    test_notification_adapter,
)
from app.modules.reminders.schemas import (
    NotificationPreferenceUpdateRequest,
    TestNotificationRequest,
)
from app.core.exceptions import EntityNotFoundError


@pytest.fixture
def test_db_session(db_session: Session):
    return db_session


@pytest.fixture
def reminder_test_env(test_db_session: Session):
    """Sets up an isolated tenant, plant, user, and master catalog for reminder testing."""
    session = test_db_session
    t_id = f"t-rem-{datetime.now().timestamp()}"
    p_id = f"p-rem-{datetime.now().timestamp()}"
    u_id = f"u-rem-{datetime.now().timestamp()}"

    tenant = Tenant(
        id=t_id,
        name="Reminder Test Corp",
        code=f"RTC-{datetime.now().microsecond}",
        is_active=True,
    )
    plant = Plant(
        id=p_id,
        tenant_id=t_id,
        name="Reminder Test Plant",
        code=f"RTP-{datetime.now().microsecond}",
        jurisdiction="Maharashtra",
        district="Pune",
        pincode="411019",
    )
    user = User(
        id=u_id,
        tenant_id=t_id,
        email=f"compliance-test-{datetime.now().microsecond}@testcorp.in",
        full_name="Rajesh Patil",
        role="EHS_MANAGER",
        hashed_password="fake-hash-pwd",
        is_active=True,
    )
    session.add_all([tenant, plant, user])

    # Setup statutory requirement
    auth = RegulatoryAuthority(
        id=f"auth-{datetime.now().timestamp()}",
        code=f"TEST-MPCB-{datetime.now().microsecond}",
        name="Test MPCB",
        jurisdiction_level="STATE",
    )
    act = RegulatoryAct(
        id=f"act-{datetime.now().timestamp()}",
        authority_id=auth.id,
        title="Water Act",
        short_name="Water Act",
        year=1974,
    )
    stat_req = StatutoryRequirement(
        id=f"sreq-{datetime.now().timestamp()}",
        act_id=act.id,
        code=f"TEST-CTO-{datetime.now().microsecond}",
        title="Consent to Operate Discharge Limits",
        description="Air and water emissions discharge thresholds",
        obligation_type="CONSENT",
        validity_period_months=12,
        grace_period_days=30,
    )
    session.add_all([auth, act, stat_req])
    session.commit()

    return {
        "tenant": tenant,
        "plant": plant,
        "user": user,
        "stat_req": stat_req,
    }


def test_notification_delivery_adapters():
    """Validates behavior of Test, Console, and SMTP notification adapters."""
    # 1. Test Adapter
    test_adapter = TestNotificationAdapter()
    test_adapter.clear()
    assert len(test_adapter.delivered_messages) == 0
    res = test_adapter.send(
        recipient="user@test.in",
        title="Title",
        message="Message",
        channel="IN_APP",
        metadata={"k": "v"},
    )
    assert res is True
    assert len(test_adapter.delivered_messages) == 1
    assert test_adapter.delivered_messages[0]["title"] == "Title"
    test_adapter.clear()
    assert len(test_adapter.delivered_messages) == 0

    # 2. Console Adapter
    console_adapter = ConsoleNotificationAdapter()
    assert console_adapter.send(
        recipient="user@test.in",
        title="Console Title",
        message="Console Msg",
        channel="EMAIL",
        metadata={},
    ) is True

    # 3. SMTP Adapter - Graceful fallback when host unconfigured
    smtp_adapter = SmtpNotificationAdapter(host=None)
    assert smtp_adapter.send(
        recipient="user@test.in",
        title="SMTP Title",
        message="SMTP Msg",
        channel="EMAIL",
        metadata={},
    ) is False

    # 4. SMTP Adapter - Dispatches when SMTP server is functional
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        live_smtp = SmtpNotificationAdapter(
            host="smtp.example.com",
            port=587,
            user="user@example.com",
            password="secretpassword",
            use_tls=True,
            from_email="alert@example.com",
            from_name="PlantProof Alerts",
        )
        delivered = live_smtp.send(
            recipient="officer@example.com",
            title="Urgent Expiry",
            message="Your permit is expiring.",
            channel="EMAIL",
            metadata={},
        )
        assert delivered is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secretpassword")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

    # 5. Factory
    assert isinstance(get_notification_adapter("test"), TestNotificationAdapter)
    assert isinstance(get_notification_adapter("console"), ConsoleNotificationAdapter)
    assert isinstance(get_notification_adapter("smtp"), SmtpNotificationAdapter)


def test_user_notification_preferences(test_db_session: Session, reminder_test_env: dict):
    """Tests retrieval, initial creation, and updates of user notification alert preferences."""
    session = test_db_session
    user = reminder_test_env["user"]
    service = ReminderService(adapter=test_notification_adapter)

    # 1. First fetch creates default preferences
    pref = service.get_or_create_preferences(session, user)
    assert pref.email_enabled is True
    assert pref.in_app_enabled is True
    assert pref.lead_time_days == 30
    assert pref.notify_on_overdue is True
    assert pref.frequency == "IMMEDIATE"

    # 2. Update preferences
    updated = service.update_preferences(
        session,
        user,
        NotificationPreferenceUpdateRequest(
            lead_time_days=60,
            notify_on_overdue=False,
            email_enabled=False,
            frequency="DAILY_DIGEST",
        ),
    )
    assert updated.lead_time_days == 60
    assert updated.notify_on_overdue is False
    assert updated.email_enabled is False
    assert updated.frequency == "DAILY_DIGEST"


def test_four_domain_reminder_scan_and_deduplication(test_db_session: Session, reminder_test_env: dict):
    """
    Verifies that run_reminder_scan scans:
    1. Tasks (due-soon & overdue)
    2. Plant Requirements (due-soon & overdue)
    3. Evidence Documents (due-soon & expired)
    4. Proposed Requirement Changes (pending human review)
    And strictly deduplicates subsequent scans on the same date.
    """
    session = test_db_session
    env = reminder_test_env
    tenant = env["tenant"]
    plant = env["plant"]
    user = env["user"]
    stat_req = env["stat_req"]

    scan_today = date(2026, 10, 28)

    # 1. Setup Task: Due in 5 days (Due-soon)
    task = ComplianceTask(
        plant_id=plant.id,
        title="Conduct Stack Emission Monitoring",
        description="Monitor flue gas emissions for DG set.",
        assigned_to_user_id=user.id,
        due_date=scan_today + timedelta(days=5),
        priority="HIGH",
        status="IN_PROGRESS",
    )
    session.add(task)

    # 2. Setup Requirement: Expired 10 days ago (Overdue)
    plant_req = PlantRequirement(
        plant_id=plant.id,
        statutory_requirement_id=stat_req.id,
        applicability_status="APPLICABLE",
        applicability_rationale="Factory operates manufacturing units subject to emissions consent.",
        evidence_status="EXPIRED",
        current_due_date=scan_today - timedelta(days=10),
    )
    session.add(plant_req)

    # 3. Setup Evidence Document: Expiring in 15 days (Due-soon)
    doc = ComplianceDocument(
        tenant_id=tenant.id,
        plant_id=plant.id,
        original_filename="MPCB_Consent_To_Operate_2026.pdf",
        storage_path="/vault/mpcb_cto.pdf",
        storage_key=f"vault-key-{datetime.now().timestamp()}",
        mime_type="application/pdf",
        file_size_bytes=1024000,
        content_hash="mock-hash-cto-pdf",
        detected_expiry_date=scan_today + timedelta(days=15),
        expiry_reminder_days=30,
        uploaded_by_user_id=user.id,
        review_status="APPROVED",
    )
    session.add(doc)

    # 4. Setup Proposed Regulatory Change: PENDING_REVIEW
    change = ProposedRequirementChange(
        plant_id=plant.id,
        statutory_requirement_id=stat_req.id,
        change_type="STATUS_MODIFIED",
        proposed_status="APPLICABLE",
        rationale="State gazette amendment on emission threshold.",
        review_status="PENDING_REVIEW",
    )
    session.add(change)
    session.commit()

    service = ReminderService(adapter=test_notification_adapter)
    test_notification_adapter.clear()

    # Configure user with email enabled
    service.update_preferences(
        session,
        user,
        NotificationPreferenceUpdateRequest(
            lead_time_days=30,
            notify_on_overdue=True,
            email_enabled=True,
            in_app_enabled=True,
        ),
    )

    # First Scan
    res1 = service.run_reminder_scan(session, tenant_id=tenant.id, as_of_date=scan_today)
    assert res1.scanned_tasks_count >= 1
    assert res1.scanned_requirements_count >= 1
    assert res1.scanned_documents_count >= 1
    assert res1.scanned_changes_count >= 1
    assert res1.generated_count >= 4
    assert res1.deduplicated_count == 0

    first_generated = res1.generated_count

    # Second Scan on the exact same date -> Deduplication must engage completely!
    res2 = service.run_reminder_scan(session, tenant_id=tenant.id, as_of_date=scan_today)
    assert res2.generated_count == 0
    assert res2.deduplicated_count >= first_generated


def test_mark_as_read_and_tenant_isolation(test_db_session: Session, reminder_test_env: dict):
    """Validates mark-as-read workflows and strict tenant boundary isolation."""
    session = test_db_session
    env = reminder_test_env
    tenant = env["tenant"]
    plant = env["plant"]
    user = env["user"]

    service = ReminderService(adapter=test_notification_adapter)

    # Dispatch a test notification
    notif_resp = service.send_test_notification(
        session,
        user,
        TestNotificationRequest(
            channel="IN_APP",
            notification_type="TEST_ALERT",
            title="Isolation Test",
            message="Ensuring cross tenant safety.",
        ),
    )
    assert notif_resp.status == "UNREAD"

    # Mark single notification as READ
    marked = service.mark_as_read(session, user, notif_resp.id)
    assert marked.status == "READ"
    assert marked.read_at is not None

    # Foreign Tenant user cannot mark read or view
    foreign_tenant = Tenant(
        id=f"t-foreign-{datetime.now().timestamp()}",
        name="Foreign Corp",
        code=f"FC-{datetime.now().microsecond}",
        is_active=True,
    )
    foreign_user = User(
        id=f"u-foreign-{datetime.now().timestamp()}",
        tenant_id=foreign_tenant.id,
        email=f"foreign-{datetime.now().microsecond}@othercorp.in",
        full_name="Foreign Officer",
        role="PLANT_MANAGER",
        hashed_password="fake",
    )
    session.add_all([foreign_tenant, foreign_user])
    session.commit()

    with pytest.raises(EntityNotFoundError):
        service.mark_as_read(session, foreign_user, notif_resp.id)

    # Foreign user notification list must be isolated
    foreign_list = service.list_notifications(session, foreign_user)
    assert foreign_list.total == 0
    assert len(foreign_list.items) == 0
