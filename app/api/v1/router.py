"""
API v1 Master Route Aggregator
"""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.modules.identity_access.router import router as auth_router
from app.modules.tenant_profile.router import router as plants_router
from app.modules.master_data.router import router as master_data_router
from app.modules.applicability.router import router as companies_router
from app.modules.applicability.admin_router import admin_router as admin_rules_router
from app.modules.regulatory_intel.router import regulatory_router
from app.modules.documents.router import documents_router
from app.modules.requirements.router import requirements_router
from app.modules.tasks.router import tasks_router
from app.modules.reminders.router import reminders_router
from app.modules.reports.router import reports_router
from app.modules.audit.router import audit_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(plants_router)
api_router.include_router(master_data_router)
api_router.include_router(companies_router)
api_router.include_router(admin_rules_router)
api_router.include_router(regulatory_router)
api_router.include_router(documents_router)
api_router.include_router(requirements_router)
api_router.include_router(tasks_router)
api_router.include_router(reminders_router)
api_router.include_router(reports_router)
api_router.include_router(audit_router)

