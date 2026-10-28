"""
Consistent Application Domain Exceptions & Error Envelope
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable plain language error message")
    remediation: Optional[str] = Field(None, description="Actionable guidance for remediation")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional context or validation errors")
    correlation_id: Optional[str] = Field(None, description="Unique trace identifier for troubleshooting")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppException(Exception):
    """Base domain exception enforcing structured error payloads."""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        remediation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.remediation = remediation
        self.details = details or {}
        super().__init__(message)


class EntityNotFoundError(AppException):
    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            code="ENTITY_NOT_FOUND",
            message=f"{entity_name} with identifier '{entity_id}' was not found.",
            status_code=404,
            remediation="Verify the identifier or check if the record was removed.",
            details={"entity": entity_name, "id": entity_id}
        )


class TenantAccessDeniedError(AppException):
    def __init__(self, message: str = "Access denied: facility or record belongs to another tenant organization."):
        super().__init__(
            code="TENANT_ACCESS_DENIED",
            message=message,
            status_code=403,
            remediation="Ensure your authenticated user credentials match the tenant organization for this facility."
        )


class InsufficientPermissionsError(AppException):
    def __init__(self, required_roles: list, current_role: str):
        super().__init__(
            code="INSUFFICIENT_PERMISSIONS",
            message=f"Role '{current_role}' is not authorized to execute this compliance operation.",
            status_code=403,
            remediation=f"This action requires one of the following roles: {', '.join(required_roles)}.",
            details={"required_roles": required_roles, "current_role": current_role}
        )


class ConflictError(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RESOURCE_CONFLICT",
            message=message,
            status_code=409,
            remediation="Check for existing records with the same code or unique key.",
            details=details
        )


class ImmutableRecordError(AppException):
    def __init__(self, entity_name: str, version_number: int):
        super().__init__(
            code="IMMUTABLE_RECORD_MODIFICATION",
            message=f"Approved {entity_name} (version {version_number}) is legally immutable and cannot be updated directly.",
            status_code=400,
            remediation="Create a new version with superseding metadata, change rationale, and review approval."
        )
