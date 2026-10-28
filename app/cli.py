"""
PlantProof Command-Line Interface (CLI)
"""

import sys
from app.core.database import engine, Base, SessionLocal
from app.seed.demo_data import seed_demo_data
# Import all models to register with Base.metadata
import app.models  # noqa: F401


def init_db():
    """Initializes database tables."""
    print("Creating database schema tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")


def run_seed():
    """Populates seed data."""
    init_db()
    print("Seeding demo personas and facility profile...")
    db = SessionLocal()
    try:
        summary = seed_demo_data(db)
        print(f"Seed complete: Tenant={summary['tenant_id']}, Plant={summary['plant_id']}")
        print(f"Active Personas: {', '.join(summary['users'])}")
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli [init-db | seed-demo-data]")
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "init-db":
        init_db()
    elif cmd == "seed-demo-data":
        run_seed()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
