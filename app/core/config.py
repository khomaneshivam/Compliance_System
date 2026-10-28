"""
Application Configuration Settings with Pydantic v2 Validation
"""

from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
