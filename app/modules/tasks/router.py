"""
Compliance Remediation Tasks Router (/api/v1/tasks)
Enforces tenant isolation, pagination, sorting, search, controlled state machine transitions,
comments, and attachment handling.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.tenancy import User
from app.modules.tasks.schemas import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskStatusTransitionRequest,
    TaskCommentCreateRequest,
    TaskAttachmentLinkRequest,
    TaskResponse,
    TaskDetailResponse,
    PaginatedTasksResponse,
    TaskCommentResponse,
    TaskAttachmentResponse,
)
from app.modules.tasks.services import task_service

tasks_router = APIRouter(prefix="/tasks", tags=["Remediation Tasks"])


@tasks_router.get("", response_model=PaginatedTasksResponse, summary="List Paginated Tasks")
def list_tasks_endpoint(
    plant_id: Optional[str] = Query(None, description="Filter by plant facility ID"),
    status: Optional[str] = Query("ALL", description="ALL, TODO, IN_PROGRESS, BLOCKED, COMPLETED"),
    priority: Optional[str] = Query("ALL", description="ALL, HIGH, MEDIUM, LOW"),
    assigned_to_user_id: Optional[str] = Query(None, description="Filter by assigned user ID"),
    plant_requirement_id: Optional[str] = Query(None, description="Filter by requirement ID"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    sort_by: str = Query("due_date", description="due_date, priority, title, created_at"),
    sort_order: str = Query("asc", description="asc, desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns server-side filtered, paginated remediation tasks for the authenticated tenant.
    Never loads all records into the browser at once.
    """
    return task_service.list_tasks(
        db=db,
        user=current_user,
        plant_id=plant_id,
        status=status,
        priority=priority,
        assigned_to_user_id=assigned_to_user_id,
        plant_requirement_id=plant_requirement_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@tasks_router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="Create Task")
def create_task_endpoint(
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new remediation task linked to a facility and optional requirement.
    """
    return task_service.create_task(db=db, user=current_user, payload=payload)


@tasks_router.get("/{task_id}", response_model=TaskDetailResponse, summary="Get Task Details")
def get_task_detail_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves full details for a task, including activity comments and attachments.
    """
    return task_service.get_task_detail(db=db, user=current_user, task_id=task_id)


@tasks_router.patch("/{task_id}", response_model=TaskResponse, summary="Update Task")
def update_task_endpoint(
    task_id: str,
    payload: TaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates task mutable attributes (title, description, due date, priority, assignee).
    """
    return task_service.update_task(db=db, user=current_user, task_id=task_id, payload=payload)


@tasks_router.post("/{task_id}/status", response_model=TaskResponse, summary="Transition Task Status")
def transition_task_status_endpoint(
    task_id: str,
    payload: TaskStatusTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Controlled state machine transitions:
    - TODO -> IN_PROGRESS, BLOCKED
    - IN_PROGRESS -> BLOCKED, COMPLETED
    - BLOCKED -> IN_PROGRESS, TODO (with mandatory explanation)
    - COMPLETED -> IN_PROGRESS (Reopened)
    """
    return task_service.transition_task_status(db=db, user=current_user, task_id=task_id, payload=payload)


@tasks_router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=status.HTTP_201_CREATED, summary="Add Task Comment")
def add_task_comment_endpoint(
    task_id: str,
    payload: TaskCommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Adds a collaborative comment or operational note to the task activity stream.
    """
    return task_service.add_comment(db=db, user=current_user, task_id=task_id, comment_text=payload.comment_text)


@tasks_router.post("/{task_id}/attachments/link", response_model=TaskAttachmentResponse, status_code=status.HTTP_201_CREATED, summary="Link Document Attachment")
def link_document_attachment_endpoint(
    task_id: str,
    payload: TaskAttachmentLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Links an existing vault compliance document to the task.
    """
    return task_service.link_document_attachment(
        db=db, user=current_user, task_id=task_id, document_id=payload.document_id
    )


@tasks_router.post("/{task_id}/attachments/upload", response_model=TaskAttachmentResponse, status_code=status.HTTP_201_CREATED, summary="Upload File Attachment")
async def upload_task_attachment_endpoint(
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads a direct file attachment to the task.
    """
    content = await file.read()
    return task_service.upload_file_attachment(
        db=db,
        user=current_user,
        task_id=task_id,
        filename=file.filename or "attachment",
        content_bytes=content,
    )


@tasks_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Task")
def delete_task_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a task (only if not completed, or by authorized role).
    """
    task_service.delete_task(db=db, user=current_user, task_id=task_id)
