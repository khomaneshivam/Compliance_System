"""
Master Data & Global Regulatory Reference Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.pagination import PageParams, PaginatedResponse
from app.modules.master_data.schemas import (
    JurisdictionResponse,
    IndustryCategoryResponse,
    BusinessActivityResponse,
    DocumentTypeResponse,
    RegulatoryAuthorityResponse,
    RegulatoryActResponse,
    StatutoryRequirementSummary,
    StatutoryRequirementDetail,
    ApplicabilityRuleSummary,
)
from app.modules.master_data.services import (
    get_all_jurisdictions,
    get_all_industry_categories,
    get_all_business_activities,
    get_all_document_types,
    get_all_authorities,
    get_all_acts,
    get_statutory_requirements_paginated,
    get_statutory_requirement_by_code,
)

router = APIRouter(prefix="/master-data", tags=["Global Master & Reference Data"])


@router.get("/jurisdictions", response_model=List[JurisdictionResponse])
def list_jurisdictions(
    level: Optional[str] = Query(None, description="Filter by CENTRAL, STATE, or LOCAL"),
    db: Session = Depends(get_db),
):
    """Lists legal jurisdictions and administrative regions."""
    return get_all_jurisdictions(db, level=level)


@router.get("/industry-categories", response_model=List[IndustryCategoryResponse])
@router.get("/industries", response_model=List[IndustryCategoryResponse])
def list_industry_categories(db: Session = Depends(get_db)):
    """Lists CPCB environmental pollution categories (Red, Orange, Green, White)."""
    return get_all_industry_categories(db)


@router.get("/business-activities", response_model=List[BusinessActivityResponse])
@router.get("/activities", response_model=List[BusinessActivityResponse])
def list_business_activities(
    category: Optional[str] = Query(None, description="Filter by sector category"),
    db: Session = Depends(get_db),
):
    """Lists manufacturing activities and standard industrial processes."""
    return get_all_business_activities(db, category=category)


@router.get("/document-types", response_model=List[DocumentTypeResponse])
def list_document_types(
    authority_id: Optional[str] = Query(None, description="Filter by issuing authority UUID"),
    db: Session = Depends(get_db),
):
    """Lists standard regulatory documents, consents, and inspection certificates."""
    return get_all_document_types(db, authority_id=authority_id)


@router.get("/authorities", response_model=List[RegulatoryAuthorityResponse])
def list_regulatory_authorities(
    jurisdiction_level: Optional[str] = Query(None, description="Filter by CENTRAL, STATE, or LOCAL"),
    db: Session = Depends(get_db),
):
    """Lists governing regulatory bodies (MPCB, DISH, CPCB, PESO, MoEFCC)."""
    return get_all_authorities(db, jurisdiction_level=jurisdiction_level)


@router.get("/acts", response_model=List[RegulatoryActResponse])
def list_regulatory_acts(
    authority_id: Optional[str] = Query(None, description="Filter by authority UUID"),
    db: Session = Depends(get_db),
):
    """Lists statutory acts, central rules, and state amendments."""
    return get_all_acts(db, authority_id=authority_id)


@router.get("/requirements", response_model=PaginatedResponse[StatutoryRequirementSummary])
def list_statutory_requirements(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, max_length=100, description="Search by code, title or scope"),
    act_id: Optional[str] = Query(None, description="Filter by act UUID"),
    obligation_type: Optional[str] = Query(None, description="Filter by LICENCE, CONSENT, CERTIFICATE, REGISTRATION, RETURN"),
    db: Session = Depends(get_db),
):
    """Lists statutory compliance requirements with search and faceted pagination."""
    page_params = PageParams(page=page, page_size=page_size, search=search)
    items, total = get_statutory_requirements_paginated(
        db, page_params, act_id=act_id, obligation_type=obligation_type
    )
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/requirements/{code}", response_model=StatutoryRequirementDetail)
def get_statutory_requirement(
    code: str,
    db: Session = Depends(get_db),
):
    """Retrieves detailed statutory obligation specification, legal references, and rule AST."""
    req = get_statutory_requirement_by_code(db, code)
    
    rules_summary = [
        ApplicabilityRuleSummary(
            id=rule.id,
            rule_version=rule.rule_version,
            status=rule.status,
            expression_ast=rule.expression_ast,
            pass_explanation_template=rule.pass_explanation_template,
            fail_explanation_template=rule.fail_explanation_template,
            is_immutable=rule.is_immutable,
            effective_from=rule.effective_from,
        )
        for rule in req.rules
    ]
    
    return StatutoryRequirementDetail(
        id=req.id,
        act_id=req.act_id,
        code=req.code,
        title=req.title,
        description=req.description,
        obligation_type=req.obligation_type,
        validity_period_months=req.validity_period_months,
        grace_period_days=req.grace_period_days,
        act_title=req.act.title if req.act else None,
        authority_code=req.act.authority.code if req.act and req.act.authority else None,
        rules=rules_summary,
    )
