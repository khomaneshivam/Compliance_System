"""
Pytest Fixtures and Test Client Setup
"""

from typing import Dict
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.rate_limit import rate_limiter
from app.models.tenancy import Plant
from app.seed.demo_data import seed_demo_data

# Use shared in-memory SQLite database for isolated test execution
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Resets sliding window rate limiter before each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Initializes tables and seeds base fixtures once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_demo_data(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Provides an isolated database session per test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    """Provides a FastAPI TestClient bound to the test database session."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers_tenant_a(client: TestClient) -> Dict[str, str]:
    """Returns Bearer authorization headers for Tenant A (Acme Manufacturing - Rohit Sharma)."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "rohit.sharma@acme-mfg.in", "password": "DemoPass123!"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_tenant_b(client: TestClient) -> Dict[str, str]:
    """Returns Bearer authorization headers for Tenant B (Beta Pharma - Vikram Singh)."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "vikram.singh@beta-pharma.in", "password": "DemoPass123!"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(client: TestClient) -> Dict[str, str]:
    """Returns Bearer authorization headers for Tenant A Admin (Amit Jadhav - ADMIN)."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "amit.jadhav@acme-mfg.in", "password": "DemoPass123!"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_viewer(client: TestClient) -> Dict[str, str]:
    """Returns Bearer authorization headers for Tenant A Viewer (Sneha Patil - VIEWER)."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "sneha.patil@acme-mfg.in", "password": "DemoPass123!"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_auditor(client: TestClient) -> Dict[str, str]:
    """Returns Bearer authorization headers for Tenant A Auditor (Vikram Mehta - AUDITOR)."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "vikram.mehta@acme-mfg.in", "password": "DemoPass123!"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant_a_plant_id(db_session) -> str:
    """Returns Plant ID for Tenant A."""
    plant = db_session.scalars(select(Plant).where(Plant.code == "MH-PUN-01")).first()
    return plant.id


@pytest.fixture
def tenant_b_plant_id(db_session) -> str:
    """Returns Plant ID for Tenant B."""
    plant = db_session.scalars(select(Plant).where(Plant.code == "GJ-AHM-01")).first()
    return plant.id
