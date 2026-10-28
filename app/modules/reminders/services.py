"""
Reminder Scheduler, Notification Dispatcher, Deduplication, and User Preferences Service
"""

import math
import smtplib
from email.message import EmailMessage
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, asc, func

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import EntityNotFoundError, TenantAccessDeniedError, AppException
from app.models.tenancy import User, Plant
from app.models.requirements import PlantRequirement
from app.models.tasks import ComplianceTask
from app.models.documents import ComplianceDocument
from app.models.assessments import ProposedRequirementChange
from app.models.reminders import ReminderNotification, UserNotificationPreference
from app.modules.reminders.schemas import (
    NotificationResponse,
    PaginatedNotificationsResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    TriggerSchedulerResponse,
    TestNotificationRequest,
)


class NotificationAdapter:
    """Base interface for dispatching notifications across delivery channels."""
    def send(self, recipient: str, title: str, message: str, channel: str, metadata: Dict[str, Any]) -> bool:
        raise NotImplementedError


class TestNotificationAdapter(NotificationAdapter):
    """
    Test and development notification adapter.
    Stores sent messages in-memory for assertion and auditing without external SMTP/SMS credentials.
    """
    __test__ = False

    def __init__(self):
        self.delivered_messages: List[Dict[str, Any]] = []

    def send(self, recipient: str, title: str, message: str, channel: str, metadata: Dict[str, Any]) -> bool:
        entry = {
            "recipient": recipient,
            "title": title,
            "message": message,
            "channel": channel,
            "metadata": metadata,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
        }
        self.delivered_messages.append(entry)
        logger.info(
            f"[TEST NOTIFICATION - {channel}] To: {recipient} | Title: {title} | Message: {message}",
            extra={"extra_data": {"recipient": recipient, "channel": channel, "metadata": metadata}}
        )
        return True

    def clear(self):
        self.delivered_messages.clear()


class ConsoleNotificationAdapter(NotificationAdapter):
    """
    Standard console logger adapter for local development and non-SMTP environments.
    """
    def send(self, recipient: str, title: str, message: str, channel: str, metadata: Dict[str, Any]) -> bool:
        logger.info(
            f"[NOTIFICATION - {channel}] To: {recipient} | Title: {title} | Message: {message}",
            extra={"extra_data": {"recipient": recipient, "channel": channel, "metadata": metadata}}
        )
        return True


class SmtpNotificationAdapter(NotificationAdapter):
    """
    Dispatches real email notifications via standard library smtplib.
    Handles TLS/SSL connections and logs failures gracefully without crashing.
    """
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        self.host = host if host is not None else settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.user = user if user is not None else settings.SMTP_USER
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_TLS
        self.from_email = from_email or settings.EMAILS_FROM_EMAIL
        self.from_name = from_name or settings.EMAILS_FROM_NAME

    def send(self, recipient: str, title: str, message: str, channel: str, metadata: Dict[str, Any]) -> bool:
        if not self.host:
            logger.warning(
                f"[SMTP SKIPPED] SMTP_HOST not configured. Notification '{title}' to '{recipient}' logged instead."
            )
            return False

        try:
            msg = EmailMessage()
            msg["Subject"] = title
            msg["From"] = f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email
            msg["To"] = recipient
            msg.set_content(message)

            if self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                if self.use_tls:
                    server.starttls()

            if self.user and self.password:
                server.login(self.user, self.password)

            server.send_message(msg)
            server.quit()
            logger.info(f"[SMTP DELIVERED] Email '{title}' sent to {recipient}")
            return True
        except Exception as exc:
            logger.error(f"[SMTP ERROR] Failed to dispatch email notification to {recipient}: {exc}")
            return False


test_notification_adapter = TestNotificationAdapter()


def get_notification_adapter(mode: Optional[str] = None) -> NotificationAdapter:
    """Factory selecting the active delivery adapter based on environment configuration."""
    selected_mode = (mode or settings.NOTIFICATION_DELIVERY_MODE or "test").lower().strip()
    if selected_mode == "smtp":
        return SmtpNotificationAdapter()
    elif selected_mode == "console":
        return ConsoleNotificationAdapter()
    return test_notification_adapter


class ReminderService:
    def __init__(self, adapter: Optional[NotificationAdapter] = None):
        self._custom_adapter = adapter

    @property
    def adapter(self) -> NotificationAdapter:
        if self._custom_adapter:
            return self._custom_adapter
        return get_notification_adapter()

    def set_adapter(self, adapter: Optional[NotificationAdapter]) -> None:
        """Sets or resets the active notification adapter."""
        self._custom_adapter = adapter

    def get_or_create_preferences(self, db: Session, user: User) -> UserNotificationPreference:
        """Retrieves or initializes user notification preferences."""
        pref = db.scalar(
            select(UserNotificationPreference).where(UserNotificationPreference.user_id == user.id)
        )
        if not pref:
            pref = UserNotificationPreference(
                tenant_id=user.tenant_id,
                user_id=user.id,
                email_enabled=True,
                in_app_enabled=True,
                lead_time_days=30,
                notify_on_overdue=True,
                frequency="IMMEDIATE",
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    def update_preferences(
        self, db: Session, user: User, payload: NotificationPreferenceUpdateRequest
    ) -> NotificationPreferenceResponse:
        """Updates user alert preferences."""
        pref = self.get_or_create_preferences(db, user)
        if payload.email_enabled is not None:
            pref.email_enabled = payload.email_enabled
        if payload.in_app_enabled is not None:
            pref.in_app_enabled = payload.in_app_enabled
        if payload.lead_time_days is not None:
            pref.lead_time_days = payload.lead_time_days
        if payload.notify_on_overdue is not None:
            pref.notify_on_overdue = payload.notify_on_overdue
        if payload.frequency is not None:
            pref.frequency = payload.frequency

        db.commit()
        db.refresh(pref)
        return NotificationPreferenceResponse(
            email_enabled=pref.email_enabled,
            in_app_enabled=pref.in_app_enabled,
            lead_time_days=pref.lead_time_days,
            notify_on_overdue=pref.notify_on_overdue,
            frequency=pref.frequency,
        )

    def list_notifications(
        self,
        db: Session,
        user: User,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedNotificationsResponse:
        """Returns paginated notifications for the authenticated user and their tenant."""
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        stmt = select(ReminderNotification).where(
            ReminderNotification.tenant_id == user.tenant_id,
            or_(ReminderNotification.user_id == user.id, ReminderNotification.user_id.is_(None)),
        )

        if status and status.upper() != "ALL":
            stmt = stmt.where(ReminderNotification.status == status.upper())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        unread_stmt = select(func.count()).where(
            ReminderNotification.tenant_id == user.tenant_id,
            or_(ReminderNotification.user_id == user.id, ReminderNotification.user_id.is_(None)),
            ReminderNotification.status == "UNREAD",
        )
        unread_count = db.scalar(unread_stmt) or 0

        stmt = stmt.order_by(desc(ReminderNotification.sent_at))
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        rows = list(db.scalars(stmt).all())
        items = [
            NotificationResponse(
                id=r.id,
                plant_id=r.plant_id,
                notification_type=r.notification_type,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                title=r.title,
                message=r.message,
                channel=r.channel,
                status=r.status,
                sent_at=r.sent_at,
                read_at=r.read_at,
                metadata_payload=r.metadata_payload or {},
            )
            for r in rows
        ]

        return PaginatedNotificationsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            unread_count=unread_count,
        )

    def mark_as_read(self, db: Session, user: User, notification_id: str) -> NotificationResponse:
        """Marks a notification as READ."""
        notif = db.get(ReminderNotification, notification_id)
        if not notif or notif.tenant_id != user.tenant_id:
            raise EntityNotFoundError("ReminderNotification", notification_id)

        notif.status = "READ"
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notif)

        return NotificationResponse(
            id=notif.id,
            plant_id=notif.plant_id,
            notification_type=notif.notification_type,
            entity_type=notif.entity_type,
            entity_id=notif.entity_id,
            title=notif.title,
            message=notif.message,
            channel=notif.channel,
            status=notif.status,
            sent_at=notif.sent_at,
            read_at=notif.read_at,
            metadata_payload=notif.metadata_payload or {},
        )

    def mark_all_as_read(self, db: Session, user: User) -> int:
        """Marks all unread notifications for the user as READ."""
        stmt = select(ReminderNotification).where(
            ReminderNotification.tenant_id == user.tenant_id,
            or_(ReminderNotification.user_id == user.id, ReminderNotification.user_id.is_(None)),
            ReminderNotification.status == "UNREAD",
        )
        notifs = list(db.scalars(stmt).all())
        now = datetime.now(timezone.utc)
        for n in notifs:
            n.status = "READ"
            n.read_at = now
        db.commit()
        return len(notifs)

    def run_reminder_scan(
        self, db: Session, tenant_id: str, as_of_date: Optional[date] = None
    ) -> TriggerSchedulerResponse:
        """
        Executes a deterministic reminder scan across four compliance domains:
        1. Open Compliance Tasks (status != COMPLETED).
        2. Applicable Plant Requirements expiring or overdue.
        3. Expiring & Expired Compliance Evidence Documents.
        4. Pending Regulatory Change Reviews (human-in-the-loop review queue).

        Enforces deduplication key: f"{today}:{entity_type}:{entity_id}:{notification_type}:{channel}"
        Dispatches through configured delivery channels (IN_APP, EMAIL) respecting user alert preferences.
        """
        scan_date = as_of_date or date.today()
        today_str = scan_date.isoformat()

        # Fetch plants for tenant
        plants = list(db.scalars(select(Plant).where(Plant.tenant_id == tenant_id)).all())
        plant_ids = [p.id for p in plants]
        if not plant_ids:
            return TriggerSchedulerResponse(
                scan_date=scan_date,
                scanned_tasks_count=0,
                scanned_requirements_count=0,
                scanned_documents_count=0,
                scanned_changes_count=0,
                generated_count=0,
                deduplicated_count=0,
            )

        generated = 0
        deduplicated = 0

        # Helper to get or default user preference
        user_pref_cache: Dict[str, UserNotificationPreference] = {}

        def get_user_pref(u_id: Optional[str]) -> Optional[UserNotificationPreference]:
            if not u_id:
                return None
            if u_id not in user_pref_cache:
                p = db.scalar(
                    select(UserNotificationPreference).where(UserNotificationPreference.user_id == u_id)
                )
                user_pref_cache[u_id] = p
            return user_pref_cache[u_id]

        def record_and_dispatch(
            plant_id: str,
            user_id: Optional[str],
            recipient_email: str,
            entity_type: str,
            entity_id: str,
            notif_type: str,
            title: str,
            message: str,
            metadata: Dict[str, Any],
            pref: Optional[UserNotificationPreference],
        ):
            nonlocal generated, deduplicated

            in_app_enabled = pref.in_app_enabled if pref else True
            email_enabled = pref.email_enabled if pref else False

            # 1. In-App Notification Channel
            if in_app_enabled:
                in_app_dedup = f"{today_str}:{entity_type}:{entity_id}:{notif_type}:IN_APP"
                existing = db.scalar(
                    select(ReminderNotification).where(ReminderNotification.dedup_key == in_app_dedup)
                )
                if existing:
                    deduplicated += 1
                else:
                    notif = ReminderNotification(
                        tenant_id=tenant_id,
                        plant_id=plant_id,
                        user_id=user_id,
                        notification_type=notif_type,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        title=title,
                        message=message,
                        channel="IN_APP",
                        status="UNREAD",
                        dedup_key=in_app_dedup,
                        metadata_payload=metadata,
                    )
                    db.add(notif)
                    self.adapter.send(
                        recipient=recipient_email,
                        title=title,
                        message=message,
                        channel="IN_APP",
                        metadata=metadata,
                    )
                    generated += 1

            # 2. Email Channel
            if email_enabled and recipient_email and "@" in recipient_email:
                email_dedup = f"{today_str}:{entity_type}:{entity_id}:{notif_type}:EMAIL"
                existing_email = db.scalar(
                    select(ReminderNotification).where(ReminderNotification.dedup_key == email_dedup)
                )
                if existing_email:
                    deduplicated += 1
                else:
                    notif_email = ReminderNotification(
                        tenant_id=tenant_id,
                        plant_id=plant_id,
                        user_id=user_id,
                        notification_type=notif_type,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        title=title,
                        message=message,
                        channel="EMAIL",
                        status="UNREAD",
                        dedup_key=email_dedup,
                        metadata_payload=metadata,
                    )
                    db.add(notif_email)
                    self.adapter.send(
                        recipient=recipient_email,
                        title=title,
                        message=message,
                        channel="EMAIL",
                        metadata=metadata,
                    )
                    generated += 1

        # ----------------------------------------------------------------------
        # 1. Scan Tasks
        # ----------------------------------------------------------------------
        tasks = list(
            db.scalars(
                select(ComplianceTask).where(
                    ComplianceTask.plant_id.in_(plant_ids),
                    ComplianceTask.status != "COMPLETED",
                )
            ).all()
        )

        for task in tasks:
            assigned_user = task.assignee
            pref = get_user_pref(task.assigned_to_user_id)
            lead_time = pref.lead_time_days if pref else 7
            notify_overdue = pref.notify_on_overdue if pref else True

            notif_type = None
            title = ""
            msg = ""

            if task.due_date < scan_date and notify_overdue:
                notif_type = "OVERDUE"
                title = f"Task Overdue: {task.title}"
                msg = f"Task '{task.title}' was due on {task.due_date.isoformat()} and remains incomplete."
            elif scan_date <= task.due_date <= (scan_date + timedelta(days=lead_time)):
                notif_type = "DUE_SOON"
                days_left = (task.due_date - scan_date).days
                title = f"Task Due in {days_left} Days: {task.title}"
                msg = f"Task '{task.title}' is due on {task.due_date.isoformat()} ({days_left} days remaining)."

            if notif_type:
                recipient = assigned_user.email if assigned_user else "plant-team@acme-mfg.in"
                record_and_dispatch(
                    plant_id=task.plant_id,
                    user_id=task.assigned_to_user_id,
                    recipient_email=recipient,
                    entity_type="TASK",
                    entity_id=task.id,
                    notif_type=notif_type,
                    title=title,
                    message=msg,
                    metadata={"due_date": task.due_date.isoformat(), "priority": task.priority, "task_id": task.id},
                    pref=pref,
                )

        # ----------------------------------------------------------------------
        # 2. Scan Requirements
        # ----------------------------------------------------------------------
        reqs = list(
            db.scalars(
                select(PlantRequirement).where(
                    PlantRequirement.plant_id.in_(plant_ids),
                    PlantRequirement.applicability_status == "APPLICABLE",
                )
            ).all()
        )

        for req in reqs:
            if not req.current_due_date:
                continue

            notif_type = None
            title = ""
            msg = ""
            code = req.statutory_requirement.code if req.statutory_requirement else "REQUIREMENT"
            req_title = req.statutory_requirement.title if req.statutory_requirement else "Statutory Obligation"

            if req.current_due_date < scan_date:
                notif_type = "OVERDUE"
                title = f"Requirement Expired: {code}"
                msg = f"The validity for {code} ({req_title}) expired on {req.current_due_date.isoformat()}."
            elif scan_date <= req.current_due_date <= (scan_date + timedelta(days=30)):
                notif_type = "DUE_SOON"
                days_left = (req.current_due_date - scan_date).days
                title = f"Requirement Expiring in {days_left} Days: {code}"
                msg = f"Requirement {code} is valid until {req.current_due_date.isoformat()} ({days_left} days remaining)."

            if notif_type:
                record_and_dispatch(
                    plant_id=req.plant_id,
                    user_id=None,  # Facility-wide obligation
                    recipient_email="compliance-team@acme-mfg.in",
                    entity_type="REQUIREMENT",
                    entity_id=req.id,
                    notif_type=notif_type,
                    title=title,
                    message=msg,
                    metadata={"due_date": req.current_due_date.isoformat(), "code": code, "requirement_id": req.id},
                    pref=None,
                )

        # ----------------------------------------------------------------------
        # 3. Scan Compliance Evidence Documents
        # ----------------------------------------------------------------------
        docs = list(
            db.scalars(
                select(ComplianceDocument).where(
                    ComplianceDocument.plant_id.in_(plant_ids),
                    ComplianceDocument.detected_expiry_date.isnot(None),
                )
            ).all()
        )

        for doc in docs:
            doc_user = db.get(User, doc.uploaded_by_user_id) if doc.uploaded_by_user_id else None
            pref = get_user_pref(doc.uploaded_by_user_id)
            lead_time = doc.expiry_reminder_days or (pref.lead_time_days if pref else 30)

            notif_type = None
            title = ""
            msg = ""

            if doc.detected_expiry_date < scan_date:
                notif_type = "OVERDUE"
                title = f"Document Expired: {doc.original_filename}"
                msg = f"Compliance evidence document '{doc.original_filename}' expired on {doc.detected_expiry_date.isoformat()}."
            elif scan_date <= doc.detected_expiry_date <= (scan_date + timedelta(days=lead_time)):
                notif_type = "DUE_SOON"
                days_left = (doc.detected_expiry_date - scan_date).days
                title = f"Document Expiring in {days_left} Days: {doc.original_filename}"
                msg = f"Compliance evidence document '{doc.original_filename}' will expire on {doc.detected_expiry_date.isoformat()} ({days_left} days remaining)."

            if notif_type:
                recipient = doc_user.email if doc_user else "plant-documents@acme-mfg.in"
                record_and_dispatch(
                    plant_id=doc.plant_id,
                    user_id=doc.uploaded_by_user_id,
                    recipient_email=recipient,
                    entity_type="DOCUMENT",
                    entity_id=doc.id,
                    notif_type=notif_type,
                    title=title,
                    message=msg,
                    metadata={
                        "expiry_date": doc.detected_expiry_date.isoformat(),
                        "filename": doc.original_filename,
                        "document_id": doc.id,
                    },
                    pref=pref,
                )

        # ----------------------------------------------------------------------
        # 4. Scan Pending Regulatory Change Reviews (Human-in-the-Loop)
        # ----------------------------------------------------------------------
        changes = list(
            db.scalars(
                select(ProposedRequirementChange).where(
                    ProposedRequirementChange.plant_id.in_(plant_ids),
                    ProposedRequirementChange.review_status == "PENDING_REVIEW",
                )
            ).all()
        )

        for change in changes:
            code = change.statutory_requirement.code if change.statutory_requirement else "STATUTORY_RULE"
            title = f"Pending Regulatory Review: {code}"
            msg = f"Regulatory change proposal ({change.change_type}) for requirement {code} is pending compliance review."

            record_and_dispatch(
                plant_id=change.plant_id,
                user_id=None,  # General compliance queue
                recipient_email="compliance-officer@acme-mfg.in",
                entity_type="REGULATORY_CHANGE",
                entity_id=change.id,
                notif_type="PENDING_REVIEW",
                title=title,
                message=msg,
                metadata={
                    "change_type": change.change_type,
                    "change_id": change.id,
                    "code": code,
                },
                pref=None,
            )

        db.commit()

        return TriggerSchedulerResponse(
            scan_date=scan_date,
            scanned_tasks_count=len(tasks),
            scanned_requirements_count=len(reqs),
            scanned_documents_count=len(docs),
            scanned_changes_count=len(changes),
            generated_count=generated,
            deduplicated_count=deduplicated,
        )

    def send_test_notification(
        self, db: Session, user: User, payload: TestNotificationRequest
    ) -> NotificationResponse:
        """Sends an immediate test notification using the configured notification adapter."""
        # Find first plant for user
        plant = db.scalar(select(Plant).where(Plant.tenant_id == user.tenant_id))
        plant_id = plant.id if plant else "plant-test"

        now_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        dedup_key = f"TEST:{user.id}:{payload.channel}:{now_str}"

        notif = ReminderNotification(
            tenant_id=user.tenant_id,
            plant_id=plant_id,
            user_id=user.id,
            notification_type=payload.notification_type,
            entity_type="TEST",
            entity_id=user.id,
            title=payload.title,
            message=payload.message,
            channel=payload.channel,
            status="UNREAD",
            dedup_key=dedup_key,
            metadata_payload={"is_test": True, "dispatched_by": user.email},
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        self.adapter.send(
            recipient=user.email,
            title=payload.title,
            message=payload.message,
            channel=payload.channel,
            metadata={"is_test": True, "notification_id": notif.id},
        )

        return NotificationResponse(
            id=notif.id,
            plant_id=notif.plant_id,
            notification_type=notif.notification_type,
            entity_type=notif.entity_type,
            entity_id=notif.entity_id,
            title=notif.title,
            message=notif.message,
            channel=notif.channel,
            status=notif.status,
            sent_at=notif.sent_at,
            read_at=notif.read_at,
            metadata_payload=notif.metadata_payload or {},
        )


reminder_service = ReminderService()
