"""
Master Data Domain Query Services
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.core.exceptions import EntityNotFoundError
from app.core.pagination import PageParams, paginate_select
from app.models.master_data import (
    Jurisdiction,
    IndustryCategory,
    BusinessActivity,
    DocumentType,
)
from app.models.catalog import (
    RegulatoryAuthority,
    RegulatoryAct,
    StatutoryRequirement,
    ApplicabilityRule,
)


def get_all_jurisdictions(db: Session, level: Optional[str] = None) -> List[Jurisdiction]:
    """Retrieves all jurisdictions, optionally filtered by level."""
    stmt = select(Jurisdiction).where(Jurisdiction.is_active == True)
    if level:
        stmt = stmt.where(Jurisdiction.level == level.upper())
    stmt = stmt.order_by(Jurisdiction.level, Jurisdiction.name)
    return list(db.scalars(stmt).all())


def get_all_industry_categories(db: Session) -> List[IndustryCategory]:
    """Retrieves all standard pollution categories (Red, Orange, Green, White)."""
    stmt = select(IndustryCategory).order_by(IndustryCategory.cpcb_score_max.desc())
    return list(db.scalars(stmt).all())


def get_all_business_activities(db: Session, category: Optional[str] = None) -> List[BusinessActivity]:
    """Retrieves standard manufacturing activities."""
    stmt = select(BusinessActivity)
    if category:
        stmt = stmt.where(BusinessActivity.category == category)
    stmt = stmt.order_by(BusinessActivity.name)
    return list(db.scalars(stmt).all())


def get_all_document_types(db: Session, authority_id: Optional[str] = None) -> List[DocumentType]:
    """Retrieves standard statutory document/evidence types."""
    stmt = select(DocumentType)
    if authority_id:
        stmt = stmt.where(DocumentType.issuing_authority_id == authority_id)
    stmt = stmt.order_by(DocumentType.name)
    return list(db.scalars(stmt).all())


def get_all_authorities(db: Session, jurisdiction_level: Optional[str] = None) -> List[RegulatoryAuthority]:
    """Retrieves regulatory authorities."""
    stmt = select(RegulatoryAuthority)
    if jurisdiction_level:
        stmt = stmt.where(RegulatoryAuthority.jurisdiction_level == jurisdiction_level.upper())
    stmt = stmt.order_by(RegulatoryAuthority.code)
    return list(db.scalars(stmt).all())


def get_all_acts(db: Session, authority_id: Optional[str] = None) -> List[RegulatoryAct]:
    """Retrieves regulatory acts."""
    stmt = select(RegulatoryAct)
    if authority_id:
        stmt = stmt.where(RegulatoryAct.authority_id == authority_id)
    stmt = stmt.order_by(RegulatoryAct.year.desc(), RegulatoryAct.title)
    return list(db.scalars(stmt).all())


def get_statutory_requirements_paginated(
    db: Session,
    page_params: PageParams,
    act_id: Optional[str] = None,
    obligation_type: Optional[str] = None,
) -> Tuple[List[StatutoryRequirement], int]:
    """Retrieves paginated statutory requirements with optional search and filters."""
    stmt = select(StatutoryRequirement)
    
    if act_id:
        stmt = stmt.where(StatutoryRequirement.act_id == act_id)
    if obligation_type:
        stmt = stmt.where(StatutoryRequirement.obligation_type == obligation_type.upper())
    if page_params.search:
        term = f"%{page_params.search.strip()}%"
        stmt = stmt.where(
            or_(
                StatutoryRequirement.code.ilike(term),
                StatutoryRequirement.title.ilike(term),
                StatutoryRequirement.description.ilike(term),
            )
        )
        
    stmt = stmt.order_by(StatutoryRequirement.code)
    return paginate_select(db, stmt, page_params)


def get_statutory_requirement_by_code(db: Session, code: str) -> StatutoryRequirement:
    """Retrieves a single requirement by its code, raising EntityNotFoundError if missing."""
    stmt = select(StatutoryRequirement).where(StatutoryRequirement.code == code)
    req = db.scalars(stmt).first()
    if not req:
        raise EntityNotFoundError("StatutoryRequirement", code)
    return req
