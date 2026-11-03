"""Facility fact quality and maker-checker verification tests."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.exceptions import ConflictError
from app.models.tenancy import Plant, Tenant, User
from app.modules.applicability.services import assemble_company_facts
from app.modules.tenant_profile.schemas import PlantProfileUpdate
from app.modules.tenant_profile.services import (
    get_or_create_plant_profile,
    update_plant_profile,
    verify_plant_profile,
)


def _create_test_plant(db_session, tenant: Tenant) -> Plant:
    plant = Plant(
        tenant_id=tenant.id,
        name="Unverified Facility Test Site",
        code=f"TEST-PROFILE-{uuid4().hex[:10].upper()}",
        jurisdiction="Maharashtra",
        district="Pune",
        pincode="411001",
    )
    db_session.add(plant)
    db_session.flush()
    return plant


def _create_admin(db_session, tenant: Tenant, suffix: str) -> User:
    user = User(
        tenant_id=tenant.id,
        email=f"profile-review-{suffix}-{uuid4().hex[:6]}@example.test",
        full_name=f"Profile Reviewer {suffix}",
        hashed_password="test-only-not-a-valid-user-password",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_new_profile_is_incomplete_and_does_not_invent_operational_facts(db_session):
    tenant = db_session.scalars(select(Tenant)).first()
    assert tenant is not None
    plant = _create_test_plant(db_session, tenant)

    profile = get_or_create_plant_profile(db_session, plant)

    assert profile.profile_status == "INCOMPLETE"
    assert profile.industry_category is None
    assert profile.sector is None
    assert profile.employee_count is None
    assert profile.connected_power_kw is None
    assert profile.effluent_discharge_kld is None
    assert profile.boiler_count is None

    facts = assemble_company_facts(db_session, plant)
    assert facts.get("industry_category") is None
    assert facts.get("employee_count") is None
    assert facts.get("connected_power_kw") is None
    assert facts.get("effluent_discharge_kld") is None
    assert facts.get("boiler_count") is None
    assert facts.get("has_boiler") is None
    assert facts.get("has_dg_set") is None
    assert facts.get("has_etp") is None
    assert facts.get("equipment_types") is None


def test_profile_verification_requires_separate_reviewer_and_unlocks_facts(db_session):
    tenant = db_session.scalars(select(Tenant)).first()
    assert tenant is not None
    plant = _create_test_plant(db_session, tenant)
    editor = _create_admin(db_session, tenant, "editor")
    reviewer = _create_admin(db_session, tenant, "reviewer")

    profile = update_plant_profile(
        db_session,
        plant,
        PlantProfileUpdate(
            industry_category="RED",
            sector="Chemicals",
            employee_count=80,
            connected_power_kw=250.0,
            effluent_discharge_kld=12.0,
            boiler_count=1,
        ),
        editor,
    )
    assert profile.profile_status == "INCOMPLETE"
    assert profile.updated_by_user_id == editor.id

    with pytest.raises(ConflictError, match="cannot verify the same revision"):
        verify_plant_profile(db_session, plant, editor, "Self-approval must be rejected.")

    verified = verify_plant_profile(db_session, plant, reviewer, "Checked against facility records.")
    assert verified.profile_status == "VERIFIED"
    assert verified.verified_by_user_id == reviewer.id
    assert verified.verified_at is not None

    facts = assemble_company_facts(db_session, plant)
    assert facts["industry_category"] == "RED"
    assert facts["employee_count"] == 80
    assert facts["connected_power_kw"] == 250.0
    assert facts["boiler_count"] == 1
    assert facts["has_boiler"] is True

    # A subsequent edit immediately invalidates the previous verification.
    update_plant_profile(
        db_session,
        plant,
        PlantProfileUpdate(connected_power_kw=300.0),
        reviewer,
    )
    db_session.refresh(verified)
    assert verified.profile_status == "INCOMPLETE"
    assert verified.verified_by_user_id is None
    assert verified.verified_at is None
    assert verified.updated_by_user_id == reviewer.id
