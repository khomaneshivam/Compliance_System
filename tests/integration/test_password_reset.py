"""Password reset token, enumeration-resistance and session invalidation tests."""

from sqlalchemy import select

from app.models.tenancy import UserPasswordResetToken


def test_password_reset_is_generic_single_use_and_revokes_old_jwts(
    client,
    db_session,
    admin_user,
    auth_headers_admin,
):
    request_response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": admin_user.email},
    )
    assert request_response.status_code == 202
    request_data = request_response.json()
    assert "If an active account exists" in request_data["message"]
    assert request_data["debug_token"]

    reset_record = db_session.scalar(
        select(UserPasswordResetToken).where(
            UserPasswordResetToken.user_id == admin_user.id,
            UserPasswordResetToken.status == "PENDING",
        )
    )
    assert reset_record is not None
    assert reset_record.token_hash != request_data["debug_token"]
    assert len(reset_record.token_hash) == 64

    complete_response = client.post(
        "/api/v1/auth/password-reset/complete",
        json={
            "token": request_data["debug_token"],
            "new_password": "New-Unique-Password-2026-PlantProof!",
        },
    )
    assert complete_response.status_code == 200

    db_session.expire_all()
    reset_record = db_session.get(UserPasswordResetToken, reset_record.id)
    db_session.refresh(admin_user)
    assert reset_record.status == "USED"
    assert admin_user.auth_version == 1

    # Existing access token was issued at auth_version 0 and must now fail.
    old_session_response = client.get("/api/v1/auth/me", headers=auth_headers_admin)
    assert old_session_response.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": admin_user.email,
            "password": "New-Unique-Password-2026-PlantProof!",
        },
    )
    assert new_login.status_code == 200
    new_token = new_login.json()["access_token"]
    new_session_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert new_session_response.status_code == 200

    replay = client.post(
        "/api/v1/auth/password-reset/complete",
        json={
            "token": request_data["debug_token"],
            "new_password": "Another-Unique-Password-2026-PlantProof!",
        },
    )
    assert replay.status_code == 410


def test_password_reset_request_does_not_disclose_unknown_accounts(client):
    known = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "unknown-person-987654@example.com"},
    )
    assert known.status_code == 202
    assert known.json()["message"] == (
        "If an active account exists for this email address, password reset instructions will be sent."
    )
    assert known.json().get("debug_token") is None


def test_new_reset_request_revokes_previous_pending_token(
    client,
    db_session,
    admin_user,
):
    first = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": admin_user.email},
    )
    assert first.status_code == 202
    first_token = first.json()["debug_token"]

    second = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": admin_user.email},
    )
    assert second.status_code == 202
    second_token = second.json()["debug_token"]
    assert first_token and second_token and first_token != second_token

    db_session.expire_all()
    records = list(
        db_session.scalars(
            select(UserPasswordResetToken)
            .where(UserPasswordResetToken.user_id == admin_user.id)
            .order_by(UserPasswordResetToken.created_at)
        ).all()
    )
    assert len(records) == 2
    assert records[0].status == "REVOKED"
    assert records[1].status == "PENDING"
