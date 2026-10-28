"""
PlantProof Command-Line Interface (CLI)
"""

import sys
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.seed.demo_data import seed_demo_data, seed_master_data
# Import all models to register with Base.metadata
import app.models  # noqa: F401


def init_db():
    """Initializes database tables."""
    if settings.ENVIRONMENT.lower() in ("production", "staging"):
        print(f"ERROR: Direct table creation via init-db is prohibited in {settings.ENVIRONMENT}. Use 'alembic upgrade head' instead.")
        sys.exit(1)
    print("Creating database schema tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")


def run_seed():
    """Populates seed data."""
    if settings.ENVIRONMENT.lower() in ("production", "staging") and not settings.SEED_DEMO_USERS:
        print(f"ERROR: Seeding demo personas is prohibited in {settings.ENVIRONMENT} without explicit SEED_DEMO_USERS=true.")
        sys.exit(1)

    if settings.ENVIRONMENT.lower() in ("development", "test") and settings.AUTO_MIGRATE_ON_STARTUP:
        init_db()
    print("Seeding demo personas and facility profile...")
    db = SessionLocal()
    try:
        summary = seed_demo_data(db, include_demo_fixtures=True)
        print(f"Seed complete: Tenant={summary.get('tenant_id')}, Plant={summary.get('plant_id')}")
        if "users" in summary:
            print(f"Active Personas: {', '.join(summary['users'])}")
    finally:
        db.close()


def run_seed_master():
    """Populates global reference master data only (production-safe)."""
    print("Seeding global reference master data...")
    db = SessionLocal()
    try:
        summary = seed_master_data(db)
        print(f"Master data seed complete. Jurisdictions={summary.get('jurisdictions_count', 0)}, Authorities={summary.get('authorities_count', 0)}, Requirements={summary.get('requirements_count', 0)}")
    finally:
        db.close()


def run_reminders():
    """Triggers deterministic compliance reminder scan across all active tenants."""
    from app.modules.reminders.services import reminder_service
    from app.models.tenancy import Tenant
    from sqlalchemy import select

    print("Running compliance reminder and alert scanner...")
    db = SessionLocal()
    try:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active == True)).all())
        total_gen = 0
        total_dedup = 0
        for t in tenants:
            res = reminder_service.run_reminder_scan(db, tenant_id=t.id)
            total_gen += res.generated_count
            total_dedup += res.deduplicated_count
            print(
                f"Tenant '{t.name}' ({t.code}): Tasks={res.scanned_tasks_count}, "
                f"Requirements={res.scanned_requirements_count}, Documents={res.scanned_documents_count}, "
                f"RegulatoryChanges={res.scanned_changes_count} | New={res.generated_count}, Dedup={res.deduplicated_count}"
            )
        print(f"Reminder scan finished. Total Generated={total_gen}, Total Deduplicated={total_dedup}")
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli [init-db | seed-demo-data | seed-master-data | run-reminders]")
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "init-db":
        init_db()
    elif cmd == "seed-demo-data":
        run_seed()
    elif cmd == "seed-master-data":
        run_seed_master()
    elif cmd == "run-reminders":
        run_reminders()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

