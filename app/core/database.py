"""
SQLAlchemy 2.0 Database Engine & Session Factory
"""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import StaticPool, NullPool
from app.core.config import settings
from app.core.logging import logger

# Dialect-specific engine options
engine_kwargs = {
    "echo": settings.DB_ECHO,
}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    # In-memory SQLite uses StaticPool, file-based uses default pool
    if ":memory:" in settings.DATABASE_URL:
        engine_kwargs["poolclass"] = StaticPool
else:
    # PostgreSQL pool settings
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection(db: Session) -> bool:
    """Performs a lightweight ping against the database."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database connection ping failed: {exc}")
        return False
