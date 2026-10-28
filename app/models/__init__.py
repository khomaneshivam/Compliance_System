"""
SQLAlchemy Domain Models Package
"""

from app.models.base import Base, TimestampedModel, generate_uuid, utc_now
from app.models.master_data import (
    Jurisdiction,
    IndustryCategory,
    BusinessActivity,
    DocumentType,
    OfficialSource,
    RegulationVersion,
    RequirementVersion,
)
from app.models.tenancy import Tenant, User, Plant
from app.models.profile import PlantProfile, PlantEquipment
from app.models.catalog import RegulatoryAuthority, RegulatoryAct, StatutoryRequirement, ApplicabilityRule
from app.models.requirements import PlantRequirement, EvidenceLink
from app.models.documents import ComplianceDocument, ExtractedField, ValidationCheck, ComplianceDocumentAudit
from app.models.regulatory import RegulatoryUpdate, AffectedRequirementMap, RegulatoryReview
from app.models.tasks import ComplianceTask, TaskComment, TaskAttachment, AuditLog
from app.models.assessments import AssessmentRun, AssessmentFinding, ProposedRequirementChange
from app.models.reminders import ReminderNotification, UserNotificationPreference
from app.models.reports import ReadinessReportJob
from app.models.regulatory_intel import (
    RegulatorySource,
    RegulatoryDocument,
    RegulatoryChangeReview,
    RegulatoryChangeImpact,
    RegulatorySourceAuditLog,
)

__all__ = [
    "Base",
    "TimestampedModel",
    "generate_uuid",
    "utc_now",
    # Global Master / Reference Data
    "Jurisdiction",
    "IndustryCategory",
    "BusinessActivity",
    "DocumentType",
    "OfficialSource",
    "RegulationVersion",
    "RequirementVersion",
    "RegulatoryAuthority",
    "RegulatoryAct",
    "StatutoryRequirement",
    "ApplicabilityRule",
    # Tenant Scoped Entities
    "Tenant",
    "User",
    "Plant",
    "PlantProfile",
    "PlantEquipment",
    "PlantRequirement",
    "EvidenceLink",
    "ComplianceDocument",
    "ExtractedField",
    "ValidationCheck",
    "ComplianceDocumentAudit",
    "RegulatoryUpdate",
    "AffectedRequirementMap",
    "RegulatoryReview",
    "ComplianceTask",
    "TaskComment",
    "TaskAttachment",
    "AuditLog",
    # Reminders and Preferences
    "ReminderNotification",
    "UserNotificationPreference",
    # Readiness Reports
    "ReadinessReportJob",
    # Assessments & Change Review
    "AssessmentRun",
    "AssessmentFinding",
    "ProposedRequirementChange",
    # Regulatory Intelligence & Ingestion
    "RegulatorySource",
    "RegulatoryDocument",
    "RegulatoryChangeReview",
    "RegulatoryChangeImpact",
    "RegulatorySourceAuditLog",
]
