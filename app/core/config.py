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
            # 1. Refuse unsafe debug settings
            if self.DEBUG:
                raise ValueError(
                    "Unsafe configuration: DEBUG must be set to False in production and staging environments."
                )

            # 2. Refuse known placeholder or default JWT signing secrets
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

            # 3. Refuse demo user provisioning in production
            if self.SEED_DEMO_USERS:
                raise ValueError(
                    "Unsafe configuration: SEED_DEMO_USERS must not be True in production or staging environments. "
                    "Demo credentials must never be provisioned in durable production deployments."
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

