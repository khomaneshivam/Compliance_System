"""
Admin Audit Log Service with Human-Readable Event Descriptions
Translates technical audit events into plain-language business descriptions.
"""

import math
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, asc, func

from app.models.tenancy import User
from app.models.tasks import AuditLog
from app.modules.audit.schemas import (
    AuditLogEntryResponse,
    PaginatedAuditLogsResponse,
)


class AuditService:
    def list_logs(
        self,
        db: Session,
        user: User,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        user_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedAuditLogsResponse:
        """Queries and formats tenant-scoped audit logs with plain-language descriptions."""
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        stmt = select(AuditLog)
        if user.role != "SUPER_ADMIN":
            stmt = stmt.where(AuditLog.tenant_id == user.tenant_id)

        if action and action.upper() != "ALL":
            stmt = stmt.where(AuditLog.action == action.upper())

        if entity_type and entity_type.upper() != "ALL":
            stmt = stmt.where(AuditLog.entity_type == entity_type.upper())

        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(AuditLog.action).like(term),
                    func.lower(AuditLog.entity_type).like(term),
                    func.lower(AuditLog.entity_id).like(term),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(desc(AuditLog.created_at))
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        logs = list(db.scalars(stmt).all())
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        items = [self._format_audit_entry(log) for log in logs]

        # Fetch distinct action types for filter dropdowns
        actions_stmt = select(AuditLog.action).distinct()
        if user.role != "SUPER_ADMIN":
            actions_stmt = actions_stmt.where(AuditLog.tenant_id == user.tenant_id)
        available_actions = sorted(list(db.scalars(actions_stmt).all()))

        entities_stmt = select(AuditLog.entity_type).distinct()
        if user.role != "SUPER_ADMIN":
            entities_stmt = entities_stmt.where(AuditLog.tenant_id == user.tenant_id)
        available_entities = sorted(list(db.scalars(entities_stmt).all()))

        return PaginatedAuditLogsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            available_actions=available_actions,
            available_entity_types=available_entities,
        )

    def _format_audit_entry(self, log: AuditLog) -> AuditLogEntryResponse:
        """Converts raw audit entry into user-friendly explanation and change summary."""
        user_name = log.user.full_name if log.user else "System"
        user_email = log.user.email if log.user else None

        desc_text, changes = self._describe_event(log, user_name)

        return AuditLogEntryResponse(
            id=log.id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            user_name=user_name,
            user_email=user_email,
            readable_description=desc_text,
            changes_summary=changes,
            timestamp=log.created_at,
            previous_state=log.previous_state,
            new_state=log.new_state or {},
        )

    def _describe_event(self, log: AuditLog, user_name: str) -> tuple[str, List[str]]:
        action = log.action
        entity_type = log.entity_type
        new_state = log.new_state or {}
        prev_state = log.previous_state or {}
        changes: List[str] = []

        if action == "TASK_CREATED":
            title = new_state.get("title", log.entity_id)
            desc = f"{user_name} created new remediation task '{title}'."
            if "priority" in new_state:
                changes.append(f"Priority set to {new_state['priority']}")
            if "due_date" in new_state:
                changes.append(f"Due date set to {new_state['due_date']}")

        elif action.startswith("TASK_STATUS_"):
            target_status = action.replace("TASK_STATUS_", "")
            prev_status = prev_state.get("status", "previous state")
            desc = f"{user_name} changed task status from {prev_status} to {target_status}."
            if target_status == "BLOCKED" and new_state.get("comment"):
                changes.append(f"Blocked reason: {new_state['comment']}")
            elif target_status == "COMPLETED":
                changes.append("Task marked as resolved.")

        elif action == "TASK_UPDATED":
            desc = f"{user_name} updated task details."
            for k in ["title", "due_date", "priority", "assigned_to"]:
                if k in new_state and k in prev_state and new_state[k] != prev_state[k]:
                    changes.append(f"Changed {k.replace('_', ' ')} from '{prev_state[k]}' to '{new_state[k]}'")

        elif action == "TASK_COMMENT_ADDED":
            desc = f"{user_name} added an activity comment on {entity_type} {log.entity_id}."
            if "comment_text" in new_state:
                changes.append(f"Comment: \"{new_state['comment_text'][:60]}...\"")

        elif action == "TASK_ATTACHMENT_LINKED":
            filename = new_state.get("filename", "document")
            desc = f"{user_name} attached compliance evidence '{filename}' to the task."

        elif action == "REGULATORY_CHANGE_PROPOSED":
            desc = f"New regulatory notification proposal registered for official review."
            if "title" in new_state:
                changes.append(f"Gazette/Notification: {new_state['title']}")

        elif action == "REGULATORY_CHANGE_REVIEWED":
            review_status = new_state.get("review_status", "UPDATED")
            desc = f"{user_name} reviewed regulatory proposal and marked as {review_status}."
            if "comment" in new_state:
                changes.append(f"Review rationale: {new_state['comment']}")

        elif action == "PROFILE_REASSESSMENT_APPLIED":
            desc = f"{user_name} updated company facility profile and triggered applicability reassessment."
            if "newly_applicable_count" in new_state:
                changes.append(f"Newly applicable obligations: {new_state['newly_applicable_count']}")
            if "exempt_count" in new_state:
                changes.append(f"Exempted obligations: {new_state['exempt_count']}")

        else:
            readable_action = action.replace("_", " ").title()
            desc = f"{user_name} performed {readable_action} on {entity_type.lower()}."
            for k, v in list(new_state.items())[:3]:
                if not isinstance(v, (dict, list)):
                    changes.append(f"{k}: {v}")

        return desc, changes


audit_service = AuditService()
