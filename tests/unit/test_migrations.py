"""
Unit Tests for Database Migrations & Version Tracking
"""

import os
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory



def test_alembic_configuration_and_revisions():
    """Verifies Alembic environment configuration and checks migration scripts."""
    alembic_cfg_path = os.path.join(os.getcwd(), "alembic.ini")
    assert os.path.exists(alembic_cfg_path), "alembic.ini must exist in project root"
    
    config = Config(alembic_cfg_path)
    script_dir = ScriptDirectory.from_config(config)
    
    # Check that revisions exist and baseline heads are discoverable
    heads = script_dir.get_heads()
    assert len(heads) == 1, "There should be exactly one active migration head"
    
    # Check that revisions are tracked in linear order
    revisions = list(script_dir.walk_revisions())
    assert len(revisions) >= 3, "Expected baseline, assessment, and regulatory intel revisions"
    doc_strings = [r.doc for r in revisions if r.doc]
    assert any("master_data_and_tenancy_baseline" in doc or "Initial" in doc for doc in doc_strings)
    assert any("assessment" in doc for doc in doc_strings)
    assert any("regulatory" in doc for doc in doc_strings)


import tempfile
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from alembic import command
from app.seed.demo_data import seed_master_data, seed_demo_data
from app.models.master_data import Jurisdiction, IndustryCategory
from app.models.catalog import RegulatoryAuthority, StatutoryRequirement
from app.models.tenancy import Tenant, User


def test_alembic_upgrade_head_from_empty_database():
    """Applies all Alembic migrations from an empty database and verifies schema integrity."""
    alembic_cfg_path = os.path.join(os.getcwd(), "alembic.ini")
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_fresh_migration.db").replace("\\", "/")
    sqlite_url = f"sqlite:///{db_file}"
    
    cfg = Config(alembic_cfg_path)
    cfg.set_main_option("sqlalchemy.url", sqlite_url)
    
    try:
        # Run upgrade head from scratch
        command.upgrade(cfg, "head")
        
        # Verify tables created
        temp_engine = sa.create_engine(sqlite_url)
        inspector = sa.inspect(temp_engine)
        table_names = set(inspector.get_table_names())
        
        expected_tables = {
            "alembic_version",
            "tenants",
            "users",
            "plants",
            "plant_profiles",
            "plant_equipment",
            "jurisdictions",
            "industry_categories",
            "regulatory_authorities",
            "regulatory_acts",
            "statutory_requirements",
            "applicability_rules",
            "compliance_tasks",
            "task_comments",
            "task_attachments",
            "compliance_documents",
            "regulatory_sources",
            "regulatory_documents",
            "regulatory_change_reviews",
            "reminder_notifications",
            "user_notification_preferences",
            "readiness_report_jobs",
            "audit_logs",
        }
        for expected in expected_tables:
            assert expected in table_names, f"Expected table '{expected}' missing from migrated database"
            
        temp_engine.dispose()
    finally:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


def test_seed_master_data_idempotent():
    """Proves that seed_master_data can be run repeatedly without duplicating global catalog rows."""
    engine = sa.create_engine("sqlite:///:memory:", poolclass=sa.pool.StaticPool)
    from app.core.database import Base
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        # First seed run
        res1 = seed_master_data(db)
        assert res1["jurisdictions_count"] >= 3
        assert res1["authorities_count"] >= 5
        assert res1["requirements_count"] >= 2
        
        j_count_1 = db.scalar(sa.select(sa.func.count(Jurisdiction.id)))
        auth_count_1 = db.scalar(sa.select(sa.func.count(RegulatoryAuthority.id)))
        req_count_1 = db.scalar(sa.select(sa.func.count(StatutoryRequirement.id)))
        
        # Second seed run (must be idempotent)
        res2 = seed_master_data(db)
        j_count_2 = db.scalar(sa.select(sa.func.count(Jurisdiction.id)))
        auth_count_2 = db.scalar(sa.select(sa.func.count(RegulatoryAuthority.id)))
        req_count_2 = db.scalar(sa.select(sa.func.count(StatutoryRequirement.id)))
        
        assert j_count_1 == j_count_2
        assert auth_count_1 == auth_count_2
        assert req_count_1 == req_count_2
    finally:
        db.close()
        engine.dispose()


def test_seed_demo_data_production_guard(monkeypatch):
    """Verifies that seed_demo_data does not create demo users or demo tenants in production mode."""
    engine = sa.create_engine("sqlite:///:memory:", poolclass=sa.pool.StaticPool)
    from app.core.database import Base
    Base.metadata.create_all(bind=engine)
    
    from app.core.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SEED_DEMO_USERS", False)
    
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        summary = seed_demo_data(db, include_demo_fixtures=True)
        # In production without SEED_DEMO_USERS, demo tenants must not be created
        tenant_count = db.scalar(sa.select(sa.func.count(Tenant.id)))
        assert tenant_count == 0, "No demo tenants should be provisioned in production mode"
        user_count = db.scalar(sa.select(sa.func.count(User.id)))
        assert user_count == 0, "No demo personas should be provisioned in production mode"
        
        # But master data must still be seeded
        j_count = db.scalar(sa.select(sa.func.count(Jurisdiction.id)))
        assert j_count >= 3
    finally:
        db.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_startup_production_fail_fast_on_initialization_error(monkeypatch):
    """Verifies that startup raises RuntimeError in production mode when initialization fails."""
    from app.core.config import settings
    from app.main import lifespan, app
    import app.main

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SEED_DEMO_USERS", False)
    
    # Mock seed_demo_data to simulate a fatal database/catalog corruption
    def broken_seed(db, include_demo_fixtures=False):
        raise ValueError("Simulated catastrophic corruption in regulatory authority catalog")

    monkeypatch.setattr(app.main, "seed_demo_data", broken_seed)
    
    with pytest.raises(RuntimeError) as exc_info:
        async with lifespan(app):
            pass
            
    assert "Startup initialization failed in production" in str(exc_info.value)


