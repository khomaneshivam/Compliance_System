"""
Master Data & Demo Persona Seed Loader
> NOTICE: All master regulatory catalogs and applicability rules seeded here
> represent ILLUSTRATIVE / UNVERIFIED DEMO DATA for development and demonstration.
> They do not constitute formal legal counsel.
"""

from datetime import date, datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.master_data import (
    Jurisdiction,
    IndustryCategory,
    BusinessActivity,
    DocumentType,
    OfficialSource,
    RegulationVersion,
    RequirementVersion,
)
from app.models.catalog import (
    RegulatoryAuthority,
    RegulatoryAct,
    StatutoryRequirement,
    ApplicabilityRule,
)
from app.models.tenancy import Tenant, User, Plant
from app.models.profile import PlantProfile, PlantEquipment
from app.models.requirements import PlantRequirement
from app.models.regulatory_intel import (
    RegulatorySource,
    RegulatoryDocument,
    RegulatoryChangeReview,
)


def seed_demo_data(db: Session) -> Dict[str, Any]:
    """Populates global reference master data and demo tenant fixtures."""
    
    # --------------------------------------------------------------------------
    # 1. Global Reference: Jurisdictions
    # --------------------------------------------------------------------------
    central = db.scalars(select(Jurisdiction).where(Jurisdiction.code == "IN-CENTRAL")).first()
    if not central:
        central = Jurisdiction(
            code="IN-CENTRAL",
            name="Government of India (Central)",
            level="CENTRAL",
            parent_id=None,
            is_active=True
        )
        db.add(central)
        db.flush()

    mh = db.scalars(select(Jurisdiction).where(Jurisdiction.code == "IN-MH")).first()
    if not mh:
        mh = Jurisdiction(
            code="IN-MH",
            name="State of Maharashtra",
            level="STATE",
            parent_id=central.id,
            is_active=True
        )
        db.add(mh)
        db.flush()

    gj = db.scalars(select(Jurisdiction).where(Jurisdiction.code == "IN-GJ")).first()
    if not gj:
        gj = Jurisdiction(
            code="IN-GJ",
            name="State of Gujarat",
            level="STATE",
            parent_id=central.id,
            is_active=True
        )
        db.add(gj)
        db.flush()

    # --------------------------------------------------------------------------
    # 2. Global Reference: CPCB Industry Categories
    # --------------------------------------------------------------------------
    categories = [
        ("RED", "Red Category (Heavy Pollution)", "CPCB PI Score 60 and above. Strict continuous online monitoring and consent renewal.", 60, 100),
        ("ORANGE", "Orange Category (Moderate Pollution)", "CPCB PI Score 41 to 59. Effluent and air emissions requiring standard controls.", 41, 59),
        ("GREEN", "Green Category (Low Pollution)", "CPCB PI Score 21 to 40. Simplified consent procedures.", 21, 40),
        ("WHITE", "White Category (Practically Non-Polluting)", "CPCB PI Score up to 20. Exempted from Consent to Operate; intimation required.", 0, 20),
    ]
    for code, name, desc, s_min, s_max in categories:
        cat = db.scalars(select(IndustryCategory).where(IndustryCategory.code == code)).first()
        if not cat:
            cat = IndustryCategory(
                code=code,
                name=name,
                description=desc,
                cpcb_score_min=s_min,
                cpcb_score_max=s_max
            )
            db.add(cat)
            db.flush()

    # --------------------------------------------------------------------------
    # 3. Global Reference: Regulatory Authorities
    # --------------------------------------------------------------------------
    authorities_meta = [
        ("MPCB", "Maharashtra Pollution Control Board", "STATE", mh.id, "https://mpcb.gov.in"),
        ("DISH", "Directorate of Industrial Safety and Health (Maharashtra)", "STATE", mh.id, "https://dish.maharashtra.gov.in"),
        ("CPCB", "Central Pollution Control Board", "CENTRAL", central.id, "https://cpcb.nic.in"),
        ("PESO", "Petroleum and Explosives Safety Organization", "CENTRAL", central.id, "https://peso.gov.in"),
        ("MoEFCC", "Ministry of Environment, Forest and Climate Change", "CENTRAL", central.id, "https://moef.gov.in"),
    ]
    authorities = {}
    for code, name, level, j_id, url in authorities_meta:
        auth = db.scalars(select(RegulatoryAuthority).where(RegulatoryAuthority.code == code)).first()
        if not auth:
            auth = RegulatoryAuthority(
                code=code,
                name=name,
                jurisdiction_level=level,
                jurisdiction_id=j_id,
                website_url=url
            )
            db.add(auth)
            db.flush()
        authorities[code] = auth

    # --------------------------------------------------------------------------
    # 4. Global Reference: Standard Document Types
    # --------------------------------------------------------------------------
    doc_types_meta = [
        ("MPCB_CTO", "Consent to Operate (Air & Water)", 60, False, authorities["MPCB"].id),
        ("BOILER_INSP_CERT", "Annual Boiler Inspection Certificate (Form VI)", 12, True, authorities["DISH"].id),
        ("HAZ_WASTE_AUTH", "Hazardous Waste Management Authorization (Form II)", 60, False, authorities["MPCB"].id),
        ("FACTORY_LICENCE", "Factory Licence Renewal (Form 4)", 12, False, authorities["DISH"].id),
        ("DG_STACK_MONITORING", "DG Set Stack Emission & Noise Test Report", 6, True, authorities["MPCB"].id),
    ]
    for code, name, validity, insp, auth_id in doc_types_meta:
        dt = db.scalars(select(DocumentType).where(DocumentType.code == code)).first()
        if not dt:
            dt = DocumentType(
                code=code,
                name=name,
                standard_validity_months=validity,
                requires_inspection=insp,
                issuing_authority_id=auth_id
            )
            db.add(dt)
            db.flush()

    # --------------------------------------------------------------------------
    # 5. Global Reference: Regulatory Acts & Statutory Requirements
    # --------------------------------------------------------------------------
    # Act: Water & Air Acts (Consent to Operate)
    cto_act = db.scalars(select(RegulatoryAct).where(RegulatoryAct.short_name == "Water & Air Act")).first()
    if not cto_act:
        cto_act = RegulatoryAct(
            authority_id=authorities["MPCB"].id,
            title="The Water Act, 1974 & The Air Act, 1981",
            short_name="Water & Air Act",
            year=1981,
            jurisdiction_id=mh.id
        )
        db.add(cto_act)
        db.flush()

    # Act: The Boilers Act, 1923
    boiler_act = db.scalars(select(RegulatoryAct).where(RegulatoryAct.short_name == "The Boilers Act")).first()
    if not boiler_act:
        boiler_act = RegulatoryAct(
            authority_id=authorities["DISH"].id,
            title="The Indian Boilers Act, 1923 and Maharashtra Boiler Rules",
            short_name="The Boilers Act",
            year=1923,
            jurisdiction_id=mh.id
        )
        db.add(boiler_act)
        db.flush()

    # Requirement: MPCB-CTO
    req_cto = db.scalars(select(StatutoryRequirement).where(StatutoryRequirement.code == "MPCB-CTO")).first()
    if not req_cto:
        req_cto = StatutoryRequirement(
            act_id=cto_act.id,
            code="MPCB-CTO",
            title="Consent to Operate (Air & Water)",
            description="Mandatory consent for manufacturing facilities discharging trade effluent or operating combustion stacks.",
            obligation_type="CONSENT",
            validity_period_months=60,
            grace_period_days=90
        )
        db.add(req_cto)
        db.flush()

        rule_cto = ApplicabilityRule(
            statutory_requirement_id=req_cto.id,
            rule_version=1,
            expression_ast={
                "operator": "OR",
                "rules": [
                    {"field": "industry_category", "operator": "IN", "value": ["RED", "ORANGE"]},
                    {"field": "effluent_discharge_kld", "operator": "GT", "value": 0},
                    {"field": "connected_power_kw", "operator": "GTE", "value": 100}
                ]
            },
            pass_explanation_template="Plant operates as {industry_category} category with {effluent_discharge_kld} KLD effluent discharge, triggering mandatory MPCB Consent to Operate under Section 25 of the Water Act.",
            fail_explanation_template="Plant is categorized under White category with zero effluent discharge and does not require Consent to Operate.",
            status="ACTIVE",
            is_immutable=True,
            effective_from=date(2020, 1, 1),
            change_rationale="Initial baseline deterministic rule for MPCB environmental consents."
        )
        db.add(rule_cto)
        db.flush()

    # Requirement: BOILER-INSP-CERT
    req_boiler = db.scalars(select(StatutoryRequirement).where(StatutoryRequirement.code == "BOILER-INSP-CERT")).first()
    if not req_boiler:
        req_boiler = StatutoryRequirement(
            act_id=boiler_act.id,
            code="BOILER-INSP-CERT",
            title="Steam Boiler Inspection Certificate (Form VI)",
            description="Annual hydraulic and visual inspection by Directorate of Industrial Safety & Boilers under Section 7/8.",
            obligation_type="CERTIFICATE",
            validity_period_months=12,
            grace_period_days=30
        )
        db.add(req_boiler)
        db.flush()

        rule_boiler = ApplicabilityRule(
            statutory_requirement_id=req_boiler.id,
            rule_version=1,
            expression_ast={
                "operator": "OR",
                "rules": [
                    {"field": "boiler_count", "operator": "GTE", "value": 1},
                    {"field": "steam_capacity_tph", "operator": "GT", "value": 0}
                ]
            },
            pass_explanation_template="Plant operates {boiler_count} steam boiler(s) with total capacity of {steam_capacity_tph} TPH, requiring annual Form VI inspection by DISH Chief Inspector of Boilers.",
            fail_explanation_template="Plant operates zero steam boilers or pressure vessels above the 22.75 litre threshold.",
            status="ACTIVE",
            is_immutable=True,
            effective_from=date(2020, 1, 1),
            change_rationale="Initial baseline rule for steam boiler statutory inspections."
        )
        db.add(rule_boiler)
        db.flush()

    # --------------------------------------------------------------------------
    # 6. Tenant & Persona Fixtures (Demo Tenant A: Acme Manufacturing)
    # --------------------------------------------------------------------------
    tenant_a = db.scalars(select(Tenant).where(Tenant.code == "acme-mfg")).first()
    if not tenant_a:
        tenant_a = Tenant(
            name="Acme Manufacturing Group",
            code="acme-mfg",
            is_active=True
        )
        db.add(tenant_a)
        db.flush()

    default_pw_hash = get_password_hash("DemoPass123!")
    users_meta = [
        ("rohit.sharma@acme-mfg.in", "Rohit Sharma", "PLANT_MANAGER", tenant_a.id),
        ("priya.deshmukh@acme-mfg.in", "Priya Deshmukh", "EHS_MANAGER", tenant_a.id),
        ("amit.jadhav@acme-mfg.in", "Amit Jadhav", "ADMIN", tenant_a.id),
        ("sneha.patil@acme-mfg.in", "Sneha Patil", "VIEWER", tenant_a.id),
        ("vikram.mehta@acme-mfg.in", "Vikram Mehta", "AUDITOR", tenant_a.id),
    ]
    for email, name, role, t_id in users_meta:
        user = db.scalars(select(User).where(User.email == email)).first()
        if not user:
            user = User(
                tenant_id=t_id,
                email=email,
                full_name=name,
                hashed_password=default_pw_hash,
                role=role,
                is_active=True
            )
            db.add(user)
            db.flush()

    # Demo Plant A: Pune Unit
    plant_a = db.scalars(select(Plant).where(Plant.code == "MH-PUN-01")).first()
    if not plant_a:
        plant_a = Plant(
            tenant_id=tenant_a.id,
            name="Acme Manufacturing Pvt. Ltd.",
            code="MH-PUN-01",
            jurisdiction="Maharashtra",
            district="Pune",
            pincode="411019"
        )
        db.add(plant_a)
        db.flush()

    # Plant Profile A
    prof_a = db.scalars(select(PlantProfile).where(PlantProfile.plant_id == plant_a.id)).first()
    if not prof_a:
        prof_a = PlantProfile(
            plant_id=plant_a.id,
            industry_category="RED",
            sector="Chemicals & Manufacturing",
            employee_count=150,
            contract_labour_count=50,
            built_up_area_sqm=15000.0,
            capital_investment_inr=120000000.0,
            connected_power_kw=1200.0,
            dg_set_capacity_kva=750.0,
            hazardous_waste_tpa=18.5,
            effluent_discharge_kld=60.0,
            boiler_count=1,
            steam_capacity_tph=4.5,
            raw_attributes={
                "midc_zone": "Chakan Industrial Area, Phase II",
                "nearest_water_body": "Indrayani River (Distance: 4.2 km)",
                "cpcb_category_code": "5001"
            }
        )
        db.add(prof_a)
        db.flush()

    # Plant Equipment A
    equip_items = [
        ("BOILER", "BLR-01", "4.5 TPH", "Thermax Ltd.", date(2022, 6, 15)),
        ("DG_SET", "DG-01", "750 kVA", "Cummins India", date(2021, 3, 10)),
        ("ETP", "ETP-01", "75 KLD", "Enviro ChemTech", date(2020, 11, 20)),
    ]
    for eq_type, tag, cap, mfr, inst_date in equip_items:
        eq = db.scalars(select(PlantEquipment).where(PlantEquipment.plant_id == plant_a.id, PlantEquipment.tag_number == tag)).first()
        if not eq:
            eq = PlantEquipment(
                plant_id=plant_a.id,
                equipment_type=eq_type,
                tag_number=tag,
                capacity=cap,
                manufacturer=mfr,
                installation_date=inst_date
            )
            db.add(eq)
            db.flush()

    # Plant Requirements for Plant A
    pl_req_cto = db.scalars(select(PlantRequirement).where(PlantRequirement.plant_id == plant_a.id, PlantRequirement.statutory_requirement_id == req_cto.id)).first()
    if not pl_req_cto:
        pl_req_cto = PlantRequirement(
            plant_id=plant_a.id,
            statutory_requirement_id=req_cto.id,
            applicability_status="APPLICABLE",
            applicability_rationale="Plant operates in Red Category with 60 KLD effluent discharge under MPCB jurisdiction.",
            evidence_status="VALID",
            current_due_date=date(2027, 4, 30),
            is_custom=False
        )
        db.add(pl_req_cto)
        db.flush()

    pl_req_boiler = db.scalars(select(PlantRequirement).where(PlantRequirement.plant_id == plant_a.id, PlantRequirement.statutory_requirement_id == req_boiler.id)).first()
    if not pl_req_boiler:
        pl_req_boiler = PlantRequirement(
            plant_id=plant_a.id,
            statutory_requirement_id=req_boiler.id,
            applicability_status="APPLICABLE",
            applicability_rationale="Plant operates 1 steam boiler (BLR-01) with 4.5 TPH steam capacity.",
            evidence_status="EXPIRING_SOON",
            current_due_date=date(2025, 6, 14),
            is_custom=False
        )
        db.add(pl_req_boiler)
        db.flush()

    # --------------------------------------------------------------------------
    # 7. Demo Tenant B: Beta Pharma Ltd. (For Multi-Tenant Isolation Testing)
    # --------------------------------------------------------------------------
    tenant_b = db.scalars(select(Tenant).where(Tenant.code == "beta-pharma")).first()
    if not tenant_b:
        tenant_b = Tenant(
            name="Beta Pharmaceuticals Ltd.",
            code="beta-pharma",
            is_active=True
        )
        db.add(tenant_b)
        db.flush()

    user_b = db.scalars(select(User).where(User.email == "vikram.singh@beta-pharma.in")).first()
    if not user_b:
        user_b = User(
            tenant_id=tenant_b.id,
            email="vikram.singh@beta-pharma.in",
            full_name="Vikram Singh",
            hashed_password=default_pw_hash,
            role="PLANT_MANAGER",
            is_active=True
        )
        db.add(user_b)
        db.flush()

    plant_b = db.scalars(select(Plant).where(Plant.code == "GJ-AHM-01")).first()
    if not plant_b:
        plant_b = Plant(
            tenant_id=tenant_b.id,
            name="Beta Pharma Ahmedabad Facility",
            code="GJ-AHM-01",
            jurisdiction="Gujarat",
            district="Ahmedabad",
            pincode="382213"
        )
        db.add(plant_b)
        db.flush()

    prof_b = db.scalars(select(PlantProfile).where(PlantProfile.plant_id == plant_b.id)).first()
    if not prof_b:
        prof_b = PlantProfile(
            plant_id=plant_b.id,
            industry_category="ORANGE",
            sector="Pharmaceutical Formulations",
            employee_count=85,
            contract_labour_count=20,
            built_up_area_sqm=8000.0,
            capital_investment_inr=50000000.0,
            connected_power_kw=450.0,
            dg_set_capacity_kva=250.0,
            hazardous_waste_tpa=4.0,
            effluent_discharge_kld=15.0,
            boiler_count=0,
            steam_capacity_tph=0.0,
            raw_attributes={"industrial_estate": "Vatva GIDC"}
        )
        db.add(prof_b)
        db.flush()

    # --------------------------------------------------------------------------
    # 8. Regulatory Sources Registry & Sample Change Review
    # --------------------------------------------------------------------------
    sources_meta = [
        ("LOCAL-FIXTURE", "PlantProof Offline Test Vault", None, "LOCAL_FIXTURE", "fixture://regulatory-vault/demo-feed", "LOCAL_FIXTURE", "ON_DEMAND", 60),
        ("IN-EGAZETTE", "The Gazette of India (e-Gazette)", None, "OFFICIAL_GAZETTE", "https://egazette.gov.in", "HTTP_SCRAPER", "DAILY", 6),
        ("MH-MPCB", "Maharashtra Pollution Control Board", authorities["MPCB"].id, "REGULATOR_PORTAL", "https://mpcb.gov.in/circulars-notifications", "HTTP_SCRAPER", "WEEKLY", 12),
        ("IN-CPCB", "Central Pollution Control Board", authorities["CPCB"].id, "REGULATOR_PORTAL", "https://cpcb.nic.in/notifications", "HTTP_SCRAPER", "WEEKLY", 12),
        ("MH-DISH", "Directorate of Industrial Safety and Health (MH)", authorities["DISH"].id, "REGULATOR_PORTAL", "https://dish.maharashtra.gov.in", "HTTP_SCRAPER", "WEEKLY", 12),
        ("IN-MOEFCC", "Ministry of Environment, Forest and Climate Change", authorities["MoEFCC"].id, "OFFICIAL_GAZETTE", "https://moef.gov.in/en/rules-regulations", "HTTP_SCRAPER", "MONTHLY", 12),
    ]
    sources = {}
    for code, name, a_id, s_type, url, ad_type, freq, r_limit in sources_meta:
        src = db.scalars(select(RegulatorySource).where(RegulatorySource.code == code)).first()
        if not src:
            src = RegulatorySource(
                code=code,
                name=name,
                authority_id=a_id,
                source_type=s_type,
                url=url,
                adapter_type=ad_type,
                scrape_frequency=freq,
                rate_limit_per_minute=r_limit,
                health_status="HEALTHY",
                last_checked_at=datetime.now(timezone.utc),
                last_successful_check_at=datetime.now(timezone.utc),
                consecutive_failures=0,
                is_active=True,
            )
            db.add(src)
            db.flush()
        sources[code] = src

    # Sample Detected Change Review item in needs_review
    sample_change = db.scalars(select(RegulatoryChangeReview).where(RegulatoryChangeReview.notification_number == "MPCB/JD-WPC/TB/2026/04")).first()
    if not sample_change and "MH-MPCB" in sources:
        sample_doc = RegulatoryDocument(
            source_id=sources["MH-MPCB"].id,
            external_id="MPCB/JD-WPC/TB/2026/04",
            title="Notification on Real-Time Online Effluent Quality Monitoring Mandate for Red and Orange Category Units",
            document_url="https://mpcb.gov.in/sites/default/files/circulars/wpc_notification_2026_04.pdf",
            published_date=date(2026, 10, 15),
            effective_date=date(2026, 12, 1),
            content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            file_size_bytes=142580,
            mime_type="application/pdf",
            page_count=3,
            sections=[
                {"section": "1. Short Title", "page": 1, "text": "This notification may be called the Maharashtra Water Pollution Continuous Monitoring Amendment Directions 2026."},
                {"section": "2. Applicability & Effluent Thresholds", "page": 2, "text": "All manufacturing units operating in the State of Maharashtra categorized as RED with effluent discharge exceeding 10.0 KLD shall install Continuous Effluent Quality Monitoring Systems (CEQMS)."}
            ],
            ingestion_status="EXTRACTED",
        )
        db.add(sample_doc)
        db.flush()

        sample_change = RegulatoryChangeReview(
            source_id=sources["MH-MPCB"].id,
            document_id=sample_doc.id,
            statutory_requirement_id=req_cto.id if 'req_cto' in locals() else None,
            notification_number="MPCB/JD-WPC/TB/2026/04",
            title="Water Pollution Prevention (Continuous Effluent Monitoring Threshold Amendment) 2026",
            published_date=date(2026, 10, 15),
            effective_date=date(2026, 12, 1),
            summary_plain_language="Lowers continuous effluent monitoring installation threshold for Red Category manufacturing facilities from 25 KLD to 10 KLD. Requires telemetry integration with MPCB regional servers within 60 days.",
            key_changes_summary=[
                "Red category effluent monitoring threshold lowered from 25 KLD to 10 KLD",
                "Mandatory telemetry integration with MPCB regional server",
                "Self-audit logging frequency increased to daily telemetry transmission"
            ],
            who_may_be_affected=[
                "Red category manufacturing plants in Maharashtra discharging between 10 KLD and 25 KLD effluent",
                "Chemical synthesis, electroplating, and dye intermediate manufacturing facilities"
            ],
            evidence_snippets=[
                {
                    "section": "Clause 2(b)",
                    "page": 2,
                    "text": "Every industrial plant in Red category discharging industrial effluent in excess of 10 KLD shall install online flowmeters and continuous analyzers.",
                    "clause": "2(b)"
                }
            ],
            proposed_categories=["Water Quality", "Environmental Monitoring", "Pollution Control"],
            confidence_score=0.94,
            confidence_band="HIGH",
            detected_change_type="AMENDMENT",
            old_text="All industrial units in Red category discharging effluent exceeding 25.0 KLD shall install Continuous Effluent Quality Monitoring Systems (CEQMS).",
            new_text="All industrial units in Red category discharging effluent exceeding 10.0 KLD shall install Continuous Effluent Quality Monitoring Systems (CEQMS) connected to MPCB portal.",
            diff_summary="Amended effluent discharge threshold from 25.0 KLD to 10.0 KLD for mandatory continuous analyzers.",
            status="needs_review",
        )
        db.add(sample_change)
        db.flush()

    db.commit()
    return {
        "tenant_a_id": tenant_a.id,
        "plant_a_id": plant_a.id,
        "tenant_b_id": tenant_b.id,
        "plant_b_id": plant_b.id,
    }
