"""
Application Configuration Settings with Pydantic v2 Validation
"""

from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_PLACEHOLDER_SECRETS = (
    "demo-insecure-secret-key-change-in-production-plantproof-compliance",
    "demo-fake-secret-key-do-not-use-in-production-plantproof-auth",
    "secret",
    "changeme",
    "password",
    "demo-secret-key",
    "insecure-secret-key",
    "supersecret",
)


class Settings(BaseSettings):
    PROJECT_NAME: str = "PlantProof"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="development, test, staging, production")
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = Field(
        default="demo-insecure-secret-key-change-in-production-plantproof-compliance",
        min_length=16,
        description="Cryptographic secret key for signing JWTs and session tokens"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 8, ge=15, description="Token TTL in minutes")

    # Seeding & Migration Policy
    SEED_DEMO_USERS: bool = Field(
        default=False,
        description="Explicitly permit demo persona and tenant seeding. Prohibited in production."
    )
    AUTO_MIGRATE_ON_STARTUP: bool = Field(
        default=True,
        description="Whether to auto-create schema tables on startup in local development/test environments."
    )
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./plantproof.db",
        description="Database connection URL (SQLite or PostgreSQL)"
    )
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=50)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False
    
    # Redis / Background Worker (Optional)
    REDIS_ENABLED: bool = False
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    
    # Document Vault Storage
    STORAGE_DIR: str = "./storage/vault"
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=25 * 1024 * 1024, ge=1024 * 1024)  # 25 MB

    # Document AI: fixtures are permitted only in development/test. Production must
    # use DISABLED until a real provider adapter is configured.
    DOCUMENT_AI_PROVIDER_MODE: Optional[str] = Field(
        default=None,
        description="fixture (development/test only), disabled, or live (requires a configured production adapter); defaults by environment",
    )

    # Notifications & Alerts Delivery
    NOTIFICATION_DELIVERY_MODE: str = Field(
        default="test",
        description="Delivery mode for notifications: 'console', 'test', or 'smtp'"
    )
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP authentication username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP authentication password")
    SMTP_TLS: bool = Field(default=True, description="Enable TLS for SMTP connections")
    PUBLIC_APP_URL: str = Field(
        default="http://localhost:5173",
        description="Public frontend origin used in invitation and account emails",
    )
    EMAILS_FROM_EMAIL: str = Field(
        default="notifications@plantproof.internal",
        description="Sender email address for compliance notifications"
    )
    EMAILS_FROM_NAME: str = Field(
        default="PlantProof Compliance",
        description="Sender display name for compliance notifications"
    )
    
    # Structured Logging
    LOG_LEVEL: str = Field(default="INFO", description="DEBUG, INFO, WARNING, ERROR, CRITICAL")
    LOG_FORMAT: str = Field(default="json", description="json or console")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = (self.ENVIRONMENT or "").lower().strip()
        is_production = env in ("production", "staging")

        if is_production:
            # Preserve clear security failure messages before checking integration configuration.
            if self.DEBUG:
                raise ValueError(
                    "Unsafe configuration: DEBUG must be set to False in production and staging environments."
                )

            secret = (self.SECRET_KEY or "").strip()
            secret_lower = secret.lower()
            is_placeholder = (
                secret in KNOWN_PLACEHOLDER_SECRETS
                or any(ph in secret_lower for ph in ("demo-insecure", "demo-fake", "placeholder", "change-in-production"))
                or len(secret) < 32
            )
            if is_placeholder:
                raise ValueError(
                    "Unsafe configuration: Production environment must not use placeholder or weak JWT secret keys. "
                    "Configure a high-entropy SECRET_KEY (at least 32 characters, e.g. via 'openssl rand -hex 32') in .env."
                )

            if self.SEED_DEMO_USERS:
                raise ValueError(
                    "Unsafe configuration: SEED_DEMO_USERS must not be True in production or staging environments. "
                    "Demo credentials must never be provisioned in durable production deployments."
                )

            delivery_mode = (self.NOTIFICATION_DELIVERY_MODE or "").strip().lower()
            if delivery_mode != "smtp" or not self.SMTP_HOST:
                raise ValueError(
                    "Production/staging requires NOTIFICATION_DELIVERY_MODE=smtp and SMTP_HOST for secure invitation and notification delivery."
                )
            public_url = (self.PUBLIC_APP_URL or "").strip().lower()
            if not public_url.startswith("https://"):
                raise ValueError("Production/staging requires PUBLIC_APP_URL to use HTTPS.")

        # Default to deterministic fixtures only in non-production environments.
        # Production/staging default to disabled; no implicit synthetic extraction.
        if not self.DOCUMENT_AI_PROVIDER_MODE:
            self.DOCUMENT_AI_PROVIDER_MODE = "disabled" if is_production else "fixture"

        ai_mode = (self.DOCUMENT_AI_PROVIDER_MODE or "").strip().lower()
        if ai_mode not in ("fixture", "disabled", "live"):
            raise ValueError("DOCUMENT_AI_PROVIDER_MODE must be fixture, disabled, or live.")
        if ai_mode == "fixture" and is_production:
            raise ValueError(
                "Unsafe configuration: synthetic document-AI fixtures are prohibited in staging and production."
            )
        if ai_mode == "live":
            raise ValueError(
                "No live document-AI adapter is currently configured. Use disabled mode until a reviewed provider adapter is installed."
            )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

