"""Integration tests for secure, one-time tenant user invitations."""

from uuid import uuid4

from sqlalchemy import select

from app.models.tenancy import User, UserInvitation


def test_invitation_creates_pending_account_and_single_use_acceptance(
    client,
    db_session,
    auth_headers_admin,
):
    email = f"invite-{uuid4().hex[:12]}@example.test"
    invite_response = client.post(
        "/api/v1/auth/users/invite",
        headers=auth_headers_admin,
        json={
            "email": email,
            "full_name": "Invited Plant Manager",
            "role": "PLANT_MANAGER",
        },
    )
    assert invite_response.status_code == 202
    invite = invite_response.json()
    assert invite["status"] == "PENDING"
    assert invite["delivery_status"] == "SENT"
    assert invite["debug_token"]
    assert invite["expires_at"]

    # No active account is provisioned by the invitation operation itself.
    assert db_session.scalar(select(User).where(User.email == email)) is None
    invitation = db_session.scalar(
        select(UserInvitation).where(UserInvitation.id == invite["invitation_id"])
    )
    assert invitation is not None
    assert invitation.status == "PENDING"
    assert len(invitation.token_hash) == 64
    assert invitation.token_hash != invite["debug_token"]
    assert invite["debug_token"] not in invitation.token_hash

    acceptance = client.post(
        "/api/v1/auth/invitations/accept",
        json={
            "token": invite["debug_token"],
            "password": "A-Strong-Unique-Password-2026!",
        },
    )
    assert acceptance.status_code == 200
    accepted_user = acceptance.json()
    assert accepted_user["email"] == email
    assert accepted_user["role"] == "PLANT_MANAGER"

    db_session.expire_all()
    invitation = db_session.get(UserInvitation, invite["invitation_id"])
    user = db_session.scalar(select(User).where(User.email == email))
    assert invitation.status == "ACCEPTED"
    assert invitation.accepted_user_id == user.id
    assert user.is_active is True

    replay = client.post(
        "/api/v1/auth/invitations/accept",
        json={
            "token": invite["debug_token"],
            "password": "Another-Strong-Password-2026!",
        },
    )
    assert replay.status_code == 410


def test_tenant_admin_cannot_invite_super_admin(
    client,
    auth_headers_admin,
):
    response = client.post(
        "/api/v1/auth/users/invite",
        headers=auth_headers_admin,
        json={
            "email": f"super-invite-{uuid4().hex[:12]}@example.test",
            "full_name": "Escalation Attempt",
            "role": "SUPER_ADMIN",
        },
    )
    assert response.status_code == 403


def test_invitation_rejects_unsupported_plant_scope(
    client,
    auth_headers_admin,
):
    response = client.post(
        "/api/v1/auth/users/invite",
        headers=auth_headers_admin,
        json={
            "email": f"scope-invite-{uuid4().hex[:12]}@example.test",
            "full_name": "Scoped Invite",
            "role": "PLANT_MANAGER",
            "plant_ids": ["plant-pune-01"],
        },
    )
    assert response.status_code == 422
