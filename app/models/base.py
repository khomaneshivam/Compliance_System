"""
Base Entity Model & Helpers
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def generate_uuid() -> str:
    """Generates a UUIDv4 string for primary keys."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Returns current datetime in UTC timezone."""
    return datetime.now(timezone.utc)


class TimestampedModel(Base):
    """Abstract base model adding id and created_at timestamps."""
    __abstract__ = True
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
