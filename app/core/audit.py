"""
Audit Logging Service
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.tasks import AuditLog


def record_audit_log(
    db: Session,
    tenant_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    new_state: Dict[str, Any],
    previous_state: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
) -> AuditLog:
    """Creates and commits an immutable audit log record."""
    log_entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_state=previous_state,
        new_state=new_state
    )
    db.add(log_entry)
    db.flush()
    return log_entry
