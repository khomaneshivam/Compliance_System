"""
Reusable Pagination, Filtering, and Sorting Schemas & Query Helpers
"""

import math
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
    sort_by: Optional[str] = Field(default=None, description="Field name to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order: asc or desc")
    search: Optional[str] = Field(default=None, max_length=100, description="Optional search term")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


def paginate_select(
    db: Session,
    stmt: Select,
    page_params: PageParams,
) -> tuple[List, int]:
    """Applies pagination offset/limit to a SQLAlchemy 2.0 Select query and computes total count."""
    # Count query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Paginate query
    offset = (page_params.page - 1) * page_params.page_size
    paginated_stmt = stmt.offset(offset).limit(page_params.page_size)
    items = list(db.scalars(paginated_stmt).all())

    return items, total
