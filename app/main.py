"""
PlantProof FastAPI Application Entry Point
"""

import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal, check_db_connection
from app.core.logging import setup_logging, logger, set_correlation_id, get_correlation_id
from app.core.exceptions import AppException
from app.api.v1.router import api_router
from app.seed.demo_data import seed_demo_data
import app.models  # noqa: F401

# Initialize structured logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown hooks."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    
    # 1. Database Schema Management Policy
    if settings.ENVIRONMENT.lower() in ("development", "test"):
        if settings.AUTO_MIGRATE_ON_STARTUP:
            logger.info("Development/Test environment: Ensuring local schema via Base.metadata.create_all()")
            Base.metadata.create_all(bind=engine)
        else:
            logger.info("Development/Test environment: AUTO_MIGRATE_ON_STARTUP disabled. Relying on Alembic migrations.")
    else:
        # Production / Staging: Strictly use Alembic schema migrations. NEVER call Base.metadata.create_all().
        logger.info("Production/Staging environment: Base.metadata.create_all() bypassed. Schema managed via Alembic.")
        # Verify database connection
        db_check = SessionLocal()
        try:
            if not check_db_connection(db_check):
                raise RuntimeError(f"Database connection ping failed during application startup in {settings.ENVIRONMENT} mode.")
        finally:
            db_check.close()
    
    # 2. Master Data & Demo Persona Initialization
    db = SessionLocal()
    try:
        is_dev_test = settings.ENVIRONMENT.lower() in ("development", "test")
        include_demo = is_dev_test and (settings.SEED_DEMO_USERS or settings.ENVIRONMENT.lower() == "development")
        
        summary = seed_demo_data(db, include_demo_fixtures=include_demo)
        logger.info(f"Master reference data initialized (demo fixtures included: {include_demo}).")
    except Exception as exc:
        if settings.ENVIRONMENT.lower() in ("production", "staging"):
            logger.critical(f"FATAL: Application initialization failed in {settings.ENVIRONMENT}: {exc}", exc_info=True)
            raise RuntimeError(f"Startup initialization failed in {settings.ENVIRONMENT}: {exc}") from exc
        else:
            logger.error(f"Error during master data seed initialization: {exc}", exc_info=True)
    finally:
        db.close()
        
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


tags_metadata = [
    {"name": "Health & Diagnostics", "description": "Liveness, readiness and operational status probes."},
    {"name": "Authentication & Identity", "description": "JWT authentication, credentials verification and user profile scopes."},
    {"name": "Plants & Company Operational Profiles", "description": "Multi-tenant plant management, operational parameters, and equipment registries."},
    {"name": "Global Master & Reference Data", "description": "Central and state regulatory catalogs, authorities, statutes, and rule versions."},
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Tenant Regulatory Intelligence & Compliance Evidence Management Platform",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_and_logging_middleware(request: Request, call_next):
    """
    Attaches a unique, sanitized Correlation ID to each request and records structured performance logs.
    Enforces security headers across all HTTP responses.
    """
    import re
    raw_cid = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or ""
    # Strictly validate correlation ID to avoid header injection, secret leakage, or excessive lengths
    if raw_cid and re.match(r"^[a-zA-Z0-9_\-]{1,64}$", raw_cid):
        cid = raw_cid
    else:
        cid = str(uuid.uuid4())

    set_correlation_id(cid)
    
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    # Security Headers (Defense-in-depth)
    response.headers["X-Correlation-ID"] = cid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    
    # Do not log spammy static docs or polling requests at info level
    if not request.url.path.startswith(("/docs", "/openapi.json", "/redoc")):
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} ({duration_ms}ms)",
            extra={"extra_data": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
            }}
        )
        
    return response


# ------------------------------------------------------------------------------
# Consistent Error Envelope Handlers
# ------------------------------------------------------------------------------

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handles domain-specific application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "remediation": exc.remediation,
                "details": exc.details,
                "correlation_id": get_correlation_id(),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Sanitizes Pydantic request validation errors into a clean, human-readable format.
    Enforces Cardinal UX Rule: never dump raw machine validation dumps.
    """
    sanitized_errors = {}
    for err in exc.errors():
        field_path = ".".join(str(loc) for loc in err.get("loc", []) if loc != "body")
        sanitized_errors[field_path or "payload"] = err.get("msg", "Invalid value")
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The compliance request payload contains validation errors.",
                "remediation": "Review the details object and correct the invalid fields.",
                "details": sanitized_errors,
                "correlation_id": get_correlation_id(),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Wraps FastAPI HTTPExceptions into standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "remediation": "Check request parameters and authorization headers.",
                "correlation_id": get_correlation_id(),
            }
        },
        headers=exc.headers or {},
    )


@app.exception_handler(Exception)
async def global_exception_sanitizer(request: Request, exc: Exception):
    """
    Enforces Cardinal UX Rule:
    Never expose raw unhandled exceptions, database error dumps, or stack traces.
    Logs the error with the active Correlation ID for engineering review.
    """
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing your compliance request.",
                "remediation": "Please try again or contact your compliance system administrator with the correlation ID.",
                "correlation_id": get_correlation_id(),
            }
        },
    )


# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
