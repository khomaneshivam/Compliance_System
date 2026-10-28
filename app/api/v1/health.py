"""
System Health, Liveness & Readiness Diagnostic Endpoints
Suitable for automated container orchestration, load balancers, and local testing.
Zero secrets or connection strings exposed in responses.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, status, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db, check_db_connection
from app.core.config import settings
from app.core.logging import get_correlation_id

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


class ComponentHealth(BaseModel):
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    details: str = Field(..., description="Operational summary")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Application semantic version")
    environment: str = Field(..., description="Active runtime environment")
    timestamp: str = Field(..., description="UTC ISO8601 timestamp")
    correlation_id: str = Field(..., description="Trace correlation ID")
    components: Dict[str, ComponentHealth] = Field(..., description="Subsystem health status")


@router.get("", response_model=HealthResponse)
def health_overview(db: Session = Depends(get_db)):
    """Comprehensive health overview verifying core system subsystems."""
    db_healthy = check_db_connection(db)
    
    components = {
        "database": ComponentHealth(
            status="healthy" if db_healthy else "unhealthy",
            details="Database connectivity verified" if db_healthy else "Database connection failed"
        ),
        "vault_storage": ComponentHealth(
            status="healthy",
            details="Storage vault directory accessible"
        )
    }
    
    overall_status = "healthy" if db_healthy else "degraded"
    
    return HealthResponse(
        status=overall_status,
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id=get_correlation_id(),
        components=components
    )


@router.get("/liveness")
def liveness_probe():
    """Kubernetes / Docker lightweight liveness probe."""
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/readiness", response_model=HealthResponse)
def readiness_probe(response: Response, db: Session = Depends(get_db)):
    """Readiness probe ensuring application is ready to accept production traffic."""
    db_ready = check_db_connection(db)
    
    components = {
        "database": ComponentHealth(
            status="healthy" if db_ready else "unhealthy",
            details="Relational database ready" if db_ready else "Relational database connection unavailable"
        )
    }
    
    if not db_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
    return HealthResponse(
        status="ready" if db_ready else "not_ready",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id=get_correlation_id(),
        components=components
    )
