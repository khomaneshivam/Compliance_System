"""
Compliance Task Service with Controlled State Machine Transitions
"""

import math
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, asc, func

from app.core.exceptions import EntityNotFoundError, TenantAccessDeniedError, AppException
from app.models.tenancy import User, Plant
from app.models.requirements import PlantRequirement
from app.models.documents import ComplianceDocument
from app.models.tasks import ComplianceTask, TaskComment, TaskAttachment, AuditLog
from app.modules.tasks.schemas import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskStatusTransitionRequest,
    TaskResponse,
    TaskDetailResponse,
    PaginatedTasksResponse,
    TaskCommentResponse,
    TaskAttachmentResponse,
)

VALID_TRANSITIONS: Dict[str, List[str]] = {
    "TODO": ["IN_PROGRESS", "BLOCKED"],
    "IN_PROGRESS": ["BLOCKED", "COMPLETED"],
    "BLOCKED": ["IN_PROGRESS", "TODO"],
    "COMPLETED": ["IN_PROGRESS"],  # Controlled Reopening
}


class TaskService:
    def list_tasks(
        self,
        db: Session,
        user: User,
        plant_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to_user_id: Optional[str] = None,
        plant_requirement_id: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "due_date",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedTasksResponse:
        """Paginated, filtered query for company compliance remediation tasks."""
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        stmt = select(ComplianceTask).join(ComplianceTask.plant)

        # Tenant isolation
        if user.role != "SUPER_ADMIN":
            stmt = stmt.where(Plant.tenant_id == user.tenant_id)

        if plant_id:
            stmt = stmt.where(ComplianceTask.plant_id == plant_id)

        if status and status.upper() != "ALL":
            stmt = stmt.where(ComplianceTask.status == status.upper())

        if priority and priority.upper() != "ALL":
            stmt = stmt.where(ComplianceTask.priority == priority.upper())

        if assigned_to_user_id:
            stmt = stmt.where(ComplianceTask.assigned_to_user_id == assigned_to_user_id)

        if plant_requirement_id:
            stmt = stmt.where(ComplianceTask.plant_requirement_id == plant_requirement_id)

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ComplianceTask.title).like(term),
                    func.lower(ComplianceTask.description).like(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Sort
        order_col = ComplianceTask.due_date
        if sort_by == "priority":
            order_col = ComplianceTask.priority
        elif sort_by == "title":
            order_col = ComplianceTask.title
        elif sort_by == "created_at":
            order_col = ComplianceTask.created_at

        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(order_col).nulls_last())
        else:
            stmt = stmt.order_by(asc(order_col).nulls_last())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        tasks = list(db.scalars(stmt).all())
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        items = [self._build_task_summary(t) for t in tasks]

        return PaginatedTasksResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def create_task(self, db: Session, user: User, payload: TaskCreateRequest) -> TaskResponse:
        """Creates a new remediation task linked to facility and optional requirement."""
        plant = db.get(Plant, payload.plant_id)
        if not plant:
            raise EntityNotFoundError("Plant", payload.plant_id)

        if user.role != "SUPER_ADMIN" and plant.tenant_id != user.tenant_id:
            raise TenantAccessDeniedError("Cannot create tasks in another organization's facility.")

        if payload.plant_requirement_id:
            req = db.get(PlantRequirement, payload.plant_requirement_id)
            if not req or req.plant_id != plant.id:
                raise EntityNotFoundError("PlantRequirement", payload.plant_requirement_id)

        task = ComplianceTask(
            plant_id=plant.id,
            plant_requirement_id=payload.plant_requirement_id,
            title=payload.title,
            description=payload.description,
            due_date=payload.due_date,
            priority=payload.priority,
            status="TODO",
            assigned_to_user_id=payload.assigned_to_user_id,
        )
        db.add(task)
        db.flush()

        # Audit log
        self._record_audit(
            db,
            user=user,
            action="TASK_CREATED",
            task=task,
            new_state={"title": task.title, "priority": task.priority, "due_date": task.due_date.isoformat()},
        )
        db.commit()
        db.refresh(task)

        return self._build_task_summary(task)

    def get_task_detail(self, db: Session, user: User, task_id: str) -> TaskDetailResponse:
        """Retrieves task detail with complete comments, attachments, and state metadata."""
        task = db.get(ComplianceTask, task_id)
        if not task:
            raise EntityNotFoundError("ComplianceTask", task_id)

        if user.role != "SUPER_ADMIN" and task.plant.tenant_id != user.tenant_id:
            raise TenantAccessDeniedError("Cross-tenant task access denied.")

        summary = self._build_task_summary(task)

        comments = [
            TaskCommentResponse(
                id=c.id,
                user_name=c.user.full_name if c.user else "System",
                user_email=c.user.email if c.user else None,
                comment_text=c.comment_text,
                created_at=c.created_at,
            )
            for c in task.comments
        ]

        attachments = [
            TaskAttachmentResponse(
                id=a.id,
                document_id=a.document_id,
                filename=a.filename,
                file_size_bytes=a.file_size_bytes,
                storage_key=a.storage_key,
                uploaded_by_email=a.uploaded_by.email if a.uploaded_by else None,
                created_at=a.created_at,
            )
            for a in task.attachments
        ]

        return TaskDetailResponse(
            **summary.model_dump(),
            comments=comments,
            attachments=attachments,
        )

    def update_task(self, db: Session, user: User, task_id: str, payload: TaskUpdateRequest) -> TaskResponse:
        """Updates task mutable attributes (title, description, due date, priority, assignee)."""
        task = db.get(ComplianceTask, task_id)
        if not task:
            raise EntityNotFoundError("ComplianceTask", task_id)

        if user.role != "SUPER_ADMIN" and task.plant.tenant_id != user.tenant_id:
            raise TenantAccessDeniedError("Cross-tenant task update denied.")

        prev_state = {
            "title": task.title,
            "due_date": task.due_date.isoformat(),
            "priority": task.priority,
            "assigned_to": task.assigned_to_user_id,
        }

        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = payload.description
        if payload.due_date is not None:
            task.due_date = payload.due_date
        if payload.priority is not None:
            task.priority = payload.priority
        if payload.assigned_to_user_id is not None:
            task.assigned_to_user_id = payload.assigned_to_user_id

        self._record_audit(
            db,
            user=user,
            action="TASK_UPDATED",
            task=task,
            prev_state=prev_state,
            new_state={
                "title": task.title,
                "due_date": task.due_date.isoformat(),
                "priority": task.priority,
                "assigned_to": task.assigned_to_user_id,
            },
        )
        db.commit()
        db.refresh(task)
        return self._build_task_summary(task)

    def transition_task_status(
        self, db: Session, user: User, task_id: str, payload: TaskStatusTransitionRequest
    ) -> TaskResponse:
        """
        Enforces controlled state machine transitions on compliance tasks.
        Valid transitions:
        - TODO -> IN_PROGRESS, BLOCKED
        - IN_PROGRESS -> BLOCKED, COMPLETED
        - BLOCKED -> IN_PROGRESS, TODO
        - COMPLETED -> IN_PROGRESS (Reopen)
        """
        task = db.get(ComplianceTask, task_id)
        if not task:
            raise EntityNotFoundError("ComplianceTask", task_id)

        if user.role != "SUPER_ADMIN" and task.plant.tenant_id != user.tenant_id:
            raise TenantAccessDeniedError("Cross-tenant task transition denied.")

        current_status = task.status
        target_status = payload.new_status.upper()

        if target_status == current_status:
            return self._build_task_summary(task)

        allowed = VALID_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise AppException(
                code="INVALID_TASK_STATUS_TRANSITION",
                message=f"Cannot transition task from '{current_status}' to '{target_status}'.",
                status_code=400,
                remediation=f"Allowed transitions from '{current_status}' are: {', '.join(allowed)}.",
                details={"current_status": current_status, "target_status": target_status, "allowed": allowed},
            )

        if target_status == "BLOCKED" and not (payload.comment and payload.comment.strip()):
            raise AppException(
                code="BLOCKED_REASON_REQUIRED",
                message="A mandatory explanation is required when marking a task as BLOCKED.",
                status_code=400,
                remediation="Provide the reason for the blockage in the transition request payload.",
            )

        now = datetime.now(timezone.utc)
        prev_status = task.status
        task.status = target_status

        if target_status == "COMPLETED":
            task.completed_at = now
            task.blocked_reason = None
        elif target_status == "BLOCKED":
            task.blocked_reason = payload.comment
        else:
            task.completed_at = None
            task.blocked_reason = None

        # Add comment if provided
        if payload.comment and payload.comment.strip():
            comment = TaskComment(
                task_id=task.id,
                user_id=user.id,
                comment_text=payload.comment.strip(),
            )
            db.add(comment)

        self._record_audit(
            db,
            user=user,
            action=f"TASK_STATUS_{target_status}",
            task=task,
            prev_state={"status": prev_status},
            new_state={"status": target_status, "comment": payload.comment},
        )
        db.commit()
        db.refresh(task)
        return self._build_task_summary(task)

    def add_comment(self, db: Session, user: User, task_id: str, comment_text: str) -> TaskCommentResponse:
        """Adds a comment to the task activity stream."""
        task = db.get(ComplianceTask, task_id)
        if not task:
            raise EntityNotFoundError("ComplianceTask", task_id)

        if user.role != "SUPER_ADMIN" and task.plant.tenant_id != user.tenant_id:
            raise TenantAccessDeniedError("Cross-tenant task comment denied.")

        comment = TaskComment(
            task_id=task.id,
            user_id=user.id,
            comment_text=comment_text.strip(),
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)

        return TaskCommentResponse(
            id=comment.id,
            user_name=user.full_name,
            user_email=user.email,
            comment_text=comment.comment_text,
            created_at=comment.created_at,
        )

    def link_document_attachment(
        self, db: Session, user: User, task_id: str, document_id: str
    ) -> TaskAttachmentResponse:
        """Links a compliance document from the vault as a task attachment."""
        task = db.get(ComplianceTask, task_id)
        if not task:
            raise EntityNotFoundError("ComplianceTask", task_id)

        doc = db.get(ComplianceDocument, document_id)
        if not doc:
            raise EntityNotFoundError("ComplianceDocument", document_id)

        if user.role != "SUPER_ADMIN" and (task.plant.tenant_id != user.tenant_id or doc.tenant_id != user.tenant_id):
            raise TenantAccessDeniedError("Cross-tenant attachment linking denied.")

        attachment = TaskAttachment(
            task_id=task.id,
            document_id=doc.id,
            filename=doc.original_filename,
            file_size_bytes=doc.file_size_bytes,
            storage_key=doc.storage_key,
            uploaded_by_user_id=user.id,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        return TaskAttachmentResponse(
            id=attachment.id,
            document_id=attachment.document_id,
            filename=attachment.filename,
            file_size_bytes=attachment.file_size_bytes,
            storage_key=attachment.storage_key,
            uploaded_by_email=user.email,
            created_at=attachment.created_at,
        )

    def _build_task_summary(self, task: ComplianceTask) -> TaskResponse:
        req = task.requirement
        stat = req.statutory_requirement if req else None

        return TaskResponse(
            id=task.id,
            plant_id=task.plant_id,
            plant_name=task.plant.name if task.plant else None,
            plant_requirement_id=task.plant_requirement_id,
            requirement_code=stat.code if stat else None,
            requirement_title=stat.title if stat else None,
            title=task.title,
            description=task.description,
            due_date=task.due_date,
            priority=task.priority,
            status=task.status,
            assigned_to_id=task.assigned_to_user_id,
            assigned_to_name=task.assignee.full_name if task.assignee else None,
            assigned_to_email=task.assignee.email if task.assignee else None,
            completed_at=task.completed_at,
            blocked_reason=task.blocked_reason,
            comments_count=len(task.comments),
            attachments_count=len(task.attachments),
            created_at=task.created_at,
        )

    def _record_audit(
        self,
        db: Session,
        user: User,
        action: str,
        task: ComplianceTask,
        prev_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
    ):
        audit = AuditLog(
            tenant_id=task.plant.tenant_id,
            user_id=user.id,
            action=action,
            entity_type="COMPLIANCE_TASK",
            entity_id=task.id,
            previous_state=prev_state,
            new_state=new_state or {},
        )
        db.add(audit)


task_service = TaskService()
