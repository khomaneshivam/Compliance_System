"""
Reminder Scheduler, Notification Dispatcher, Deduplication, and User Preferences Service
"""

import math
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, asc, func

from app.core.exceptions import EntityNotFoundError, TenantAccessDeniedError, AppException
from app.models.tenancy import User, Plant
from app.models.requirements import PlantRequirement
from app.models.tasks import ComplianceTask
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
    """Base interface for dispatching notifications across channels."""
    def send(self, recipient: str, title: str, message: str, channel: str, metadata: Dict[str, Any]) -> bool:
        raise NotImplementedError


class TestNotificationAdapter(NotificationAdapter):
    """
    Test and development notification adapter.
    Stores sent messages in-memory for assertion and auditing without external SMTP/SMS credentials.
    """
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
        return True

    def clear(self):
        self.delivered_messages.clear()


test_notification_adapter = TestNotificationAdapter()


class ReminderService:
    def __init__(self, adapter: Optional[NotificationAdapter] = None):
        self.adapter = adapter or test_notification_adapter

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
        Executes a deterministic reminder scan for overdue and due-soon work:
        1. Open Compliance Tasks (status != COMPLETED).
        2. Applicable Plant Requirements expiring or overdue.
        Enforces deduplication key: f"{today}:{entity_type}:{entity_id}:{notification_type}:{channel}"
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
                generated_count=0,
                deduplicated_count=0,
            )

        # 1. Scan Tasks
        tasks = list(
            db.scalars(
                select(ComplianceTask).where(
                    ComplianceTask.plant_id.in_(plant_ids),
                    ComplianceTask.status != "COMPLETED",
                )
            ).all()
        )

        generated = 0
        deduplicated = 0

        for task in tasks:
            assigned_user = task.assignee
            lead_time = 7
            notify_overdue = True
            if assigned_user:
                pref = db.scalar(
                    select(UserNotificationPreference).where(
                        UserNotificationPreference.user_id == assigned_user.id
                    )
                )
                if pref:
                    lead_time = pref.lead_time_days
                    notify_overdue = pref.notify_on_overdue

            notif_type = None
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
                dedup_key = f"{today_str}:TASK:{task.id}:{notif_type}:IN_APP"
                existing = db.scalar(
                    select(ReminderNotification).where(ReminderNotification.dedup_key == dedup_key)
                )
                if existing:
                    deduplicated += 1
                else:
                    notif = ReminderNotification(
                        tenant_id=tenant_id,
                        plant_id=task.plant_id,
                        user_id=task.assigned_to_user_id,
                        notification_type=notif_type,
                        entity_type="TASK",
                        entity_id=task.id,
                        title=title,
                        message=msg,
                        channel="IN_APP",
                        status="UNREAD",
                        dedup_key=dedup_key,
                        metadata_payload={"due_date": task.due_date.isoformat(), "priority": task.priority},
                    )
                    db.add(notif)
                    self.adapter.send(
                        recipient=assigned_user.email if assigned_user else "plant-team",
                        title=title,
                        message=msg,
                        channel="IN_APP",
                        metadata={"task_id": task.id},
                    )
                    generated += 1

        # 2. Scan Requirements
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
            if req.current_due_date < scan_date:
                notif_type = "OVERDUE"
                title = f"Requirement Expired: {req.statutory_requirement.code}"
                msg = f"The validity for {req.statutory_requirement.code} ({req.statutory_requirement.title}) expired on {req.current_due_date.isoformat()}."
            elif scan_date <= req.current_due_date <= (scan_date + timedelta(days=30)):
                notif_type = "DUE_SOON"
                days_left = (req.current_due_date - scan_date).days
                title = f"Requirement Expiring in {days_left} Days: {req.statutory_requirement.code}"
                msg = f"Requirement {req.statutory_requirement.code} is valid until {req.current_due_date.isoformat()}."

            if notif_type:
                dedup_key = f"{today_str}:REQUIREMENT:{req.id}:{notif_type}:IN_APP"
                existing = db.scalar(
                    select(ReminderNotification).where(ReminderNotification.dedup_key == dedup_key)
                )
                if existing:
                    deduplicated += 1
                else:
                    notif = ReminderNotification(
                        tenant_id=tenant_id,
                        plant_id=req.plant_id,
                        user_id=None,  # General plant alert
                        notification_type=notif_type,
                        entity_type="REQUIREMENT",
                        entity_id=req.id,
                        title=title,
                        message=msg,
                        channel="IN_APP",
                        status="UNREAD",
                        dedup_key=dedup_key,
                        metadata_payload={"due_date": req.current_due_date.isoformat(), "code": req.statutory_requirement.code},
                    )
                    db.add(notif)
                    self.adapter.send(
                        recipient="plant-team",
                        title=title,
                        message=msg,
                        channel="IN_APP",
                        metadata={"requirement_id": req.id},
                    )
                    generated += 1

        db.commit()

        return TriggerSchedulerResponse(
            scan_date=scan_date,
            scanned_tasks_count=len(tasks),
            scanned_requirements_count=len(reqs),
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
        dedup_key = f"TEST:{user.id}:{now_str}"

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
