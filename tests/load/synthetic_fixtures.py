"""
Synthetic Load Fixture Generator
Generates scaled, deterministic test fixtures for multi-tenant load testing
without real customer, PII, or confidential manufacturing operational data.
"""

import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.tenancy import Tenant, User, Plant
from app.models.profile import PlantProfile
from app.models.catalog import StatutoryRequirement, ApplicabilityRule
from app.models.documents import ComplianceDocument
from app.models.tasks import ComplianceTask
from app.models.requirements import PlantRequirement


def generate_synthetic_load_dataset(
    db: Session,
    tenant_count: int = 3,
    plants_per_tenant: int = 2,
    tasks_per_plant: int = 10,
    documents_per_plant: int = 5,
) -> Dict[str, Any]:
    """
    Seeds scaled synthetic entities for load testing.
    All data is clearly tagged with 'LOAD_TEST_' prefixes.
    """
    seeded_tenants: List[str] = []
    seeded_plants: List[str] = []
    seeded_users: List[str] = []
    
    password_hash = get_password_hash("DemoPass123!")

    # Check for existing base requirements
    reqs = db.scalars(select(StatutoryRequirement)).all()
    if not reqs:
        # Create a basic synthetic requirement if none exist
        base_req = StatutoryRequirement(
            code="LOAD-REQ-ENV-01",
            title="Synthetic Industrial Emission Monitoring Standard",
            description="Synthetic requirement for load testing.",
            obligation_type="RETURN",
            jurisdiction_level="STATE"
        )
        db.add(base_req)
        db.commit()
        reqs = [base_req]

    for t_idx in range(1, tenant_count + 1):
        t_code = f"LOAD-TENANT-{t_idx:02d}"
        
        # Check if already seeded
        tenant = db.scalars(select(Tenant).where(Tenant.code == t_code)).first()
        if not tenant:
            tenant = Tenant(
                name=f"Synthetic Industrial Enterprise {t_idx:02d}",
                code=t_code,
                is_active=True
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        seeded_tenants.append(tenant.id)

        # Create Plant Manager user for tenant
        user_email = f"manager.load{t_idx}@synthetic-mfg.in"
        user = db.scalars(select(User).where(User.email == user_email)).first()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email=user_email,
                full_name=f"Load Persona {t_idx}",
                hashed_password=password_hash,
                role="PLANT_MANAGER",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        seeded_users.append(user.email)

        # Create plants
        for p_idx in range(1, plants_per_tenant + 1):
            p_code = f"LOAD-P{t_idx:02d}-{p_idx:02d}"
            plant = db.scalars(select(Plant).where(Plant.code == p_code)).first()
            if not plant:
                plant = Plant(
                    tenant_id=tenant.id,
                    name=f"Synthetic Factory Unit {p_code}",
                    code=p_code,
                    jurisdiction="Maharashtra" if p_idx % 2 == 1 else "Gujarat",
                    district="Pune" if p_idx % 2 == 1 else "Ahmedabad",
                    pincode="411001",
                )
                db.add(plant)
                db.commit()
                db.refresh(plant)

                # Attach profile
                profile = PlantProfile(
                    plant_id=plant.id,
                    industry_category="RED" if p_idx == 1 else "ORANGE",
                    boiler_count=2,
                    steam_capacity_tph=5.0,
                    hazardous_waste_tpa=12.5,
                    effluent_discharge_kld=25.0,
                    raw_attributes={"hazardous_chemicals_kg": 1200.0}
                )
                db.add(profile)
                db.commit()

            seeded_plants.append(plant.id)

            # Seed plant obligations
            for req in reqs:
                existing_ob = db.scalars(
                    select(PlantRequirement).where(
                        PlantRequirement.plant_id == plant.id,
                        PlantRequirement.statutory_requirement_id == req.id
                    )
                ).first()
                if not existing_ob:
                    ob = PlantRequirement(
                        plant_id=plant.id,
                        statutory_requirement_id=req.id,
                        applicability_status="APPLICABLE",
                        evidence_status="MISSING" if p_idx == 1 else "VALID",
                        applicability_rationale="Synthetic load test baseline assessment."
                    )
                    db.add(ob)

            # Seed compliance tasks
            from datetime import date, timedelta
            for k_idx in range(1, tasks_per_plant + 1):
                task = ComplianceTask(
                    plant_id=plant.id,
                    title=f"LOAD TASK {p_code}-{k_idx:03d}: Periodic Inspection",
                    description="Routine synthetic compliance task for load benchmarking.",
                    due_date=date.today() + timedelta(days=k_idx * 5),
                    status="TODO" if k_idx % 2 == 1 else "COMPLETED",
                    priority="HIGH" if k_idx <= 2 else "MEDIUM"
                )
                db.add(task)

            # Seed compliance document metadata
            for d_idx in range(1, documents_per_plant + 1):
                doc = ComplianceDocument(
                    tenant_id=tenant.id,
                    plant_id=plant.id,
                    original_filename=f"synthetic_doc_{p_code}_{d_idx}.pdf",
                    storage_path=f"storage/vault/{tenant.id}/synthetic_doc_{p_code}_{d_idx}.pdf",
                    storage_key=f"synthetic-key-{p_code}-{d_idx}",
                    file_size_bytes=1024 * 128,  # 128 KB
                    content_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                    mime_type="application/pdf",
                    review_status="APPROVED" if d_idx % 2 == 1 else "PENDING_REVIEW"
                )
                db.add(doc)

            db.commit()

    return {
        "tenants": len(seeded_tenants),
        "plants": len(seeded_plants),
        "users": len(seeded_users),
        "sample_user": seeded_users[0] if seeded_users else "rohit.sharma@acme-mfg.in",
        "sample_plant": seeded_plants[0] if seeded_plants else None
    }
