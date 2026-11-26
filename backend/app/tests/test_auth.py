import pytest
import hashlib
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db, Base
from app.db import models
from app.auth import security

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth_hardened.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Setup fresh tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_register_normalization_and_enumeration_prevention(client, db_session):
    # Test normalization on registration and generic message
    resp = client.post("https://testserver/api/v1/auth/register", json={
        "email": "   TEST.User@Uni.EDU   ",
        "password": "Password123!",
        "full_name": "Test Normalize"
    })
    assert resp.status_code == 200
    assert "Registration successful" in resp.json()["message"]

    # Verify user exists in database with normalized lowercase email
    user = db_session.query(models.User).filter(models.User.email == "test.user@uni.edu").first()
    assert user is not None
    assert user.is_verified is False

    # Test registration user enumeration prevention (duplicate)
    resp_dup = client.post("https://testserver/api/v1/auth/register", json={
        "email": "test.user@uni.edu",
        "password": "Password123!",
        "full_name": "Test Duplicate"
    })
    # Must return exact same generic message and code 200, but do not create duplicate
    assert resp_dup.status_code == 200
    assert "Registration successful" in resp_dup.json()["message"]

    users_count = db_session.query(models.User).filter(models.User.email == "test.user@uni.edu").count()
    assert users_count == 1


def test_token_hashing_in_database(client, db_session):
    # Register user
    client.post("https://testserver/api/v1/auth/register", json={
        "email": "hash@uni.edu",
        "password": "Password123!",
        "full_name": "Hash User"
    })

    # Retrieve user from DB
    user = db_session.query(models.User).filter(models.User.email == "hash@uni.edu").first()
    assert user.verification_token_hash is not None
    # Verify we did NOT store raw token
    # The hash should be a 64-char sha256 hex string
    assert len(user.verification_token_hash) == 64
    assert not user.verification_token_hash.startswith("http")


def test_login_lockout_and_timing_dummy_attacks(client, db_session):
    # Register and verify account
    client.post("https://testserver/api/v1/auth/register", json={
        "email": "lockout@uni.edu",
        "password": "Password123!",
        "full_name": "Lockout User"
    })
    user = db_session.query(models.User).filter(models.User.email == "lockout@uni.edu").first()
    user.is_verified = True
    db_session.commit()

    # Fail login 5 times
    for _ in range(5):
        resp = client.post("https://testserver/api/v1/auth/login", data={
            "username": "lockout@uni.edu",
            "password": "WrongPassword!"
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Incorrect email or password."

    # 6th attempt locks out account
    resp = client.post("https://testserver/api/v1/auth/login", data={
        "username": "lockout@uni.edu",
        "password": "Password123!"
    })
    assert resp.status_code == 429
    assert "Too many failed login attempts" in resp.json()["detail"]

    # Test login user enumeration prevention (should return same 401 for unknown user)
    resp_unknown = client.post("https://testserver/api/v1/auth/login", data={
        "username": "unknown@uni.edu",
        "password": "Password123!"
    })
    assert resp_unknown.status_code == 401
    assert resp_unknown.json()["detail"] == "Incorrect email or password."


def test_dual_password_hashing_and_upgrade(client, db_session):
    # Simulate a user created previously using standard bcrypt
    legacy_bcrypt_context = security.CryptContext(schemes=["bcrypt"], deprecated="auto")
    legacy_hash = legacy_bcrypt_context.hash("BcryptPassword123!")

    legacy_user = models.User(
        email="legacy@uni.edu",
        hashed_password=legacy_hash,
        full_name="Legacy User",
        role="user",
        is_active=True,
        is_verified=True
    )
    db_session.add(legacy_user)
    db_session.commit()

    # Log in with the legacy account
    resp = client.post("https://testserver/api/v1/auth/login", data={
        "username": "legacy@uni.edu",
        "password": "BcryptPassword123!"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    # Verify password hash was dynamically upgraded in database to Argon2id
    db_session.refresh(legacy_user)
    assert legacy_user.hashed_password.startswith("$argon2id$")


def test_refresh_token_rotation_and_theft_detection(client, db_session):
    # Register and verify
    client.post("https://testserver/api/v1/auth/register", json={
        "email": "refresh@uni.edu",
        "password": "Password123!",
        "full_name": "Refresh User"
    })
    user = db_session.query(models.User).filter(models.User.email == "refresh@uni.edu").first()
    user.is_verified = True
    db_session.commit()

    # Login to retrieve tokens
    resp = client.post("https://testserver/api/v1/auth/login", data={
        "username": "refresh@uni.edu",
        "password": "Password123!"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    # Check that refresh token cookie is set
    cookie = client.cookies.get("refresh_token")
    assert cookie is not None

    # Call /refresh to rotate token
    resp_refresh = client.post("https://testserver/api/v1/auth/refresh")
    assert resp_refresh.status_code == 200
    assert "access_token" in resp_refresh.json()

    # Check new cookie was issued (rotation)
    new_cookie = client.cookies.get("refresh_token")
    assert new_cookie != cookie

    # Test token theft detection: try to reuse the old/invalidated cookie
    client.cookies.clear()
    client.cookies.set("refresh_token", cookie, domain="testserver.local", path="/")
    resp_reuse = client.post("https://testserver/api/v1/auth/refresh")
    assert resp_reuse.status_code == 401
    assert "Session has expired" in resp_reuse.json()["detail"]

    # Verify ALL user sessions have been revoked
    db_session.expire_all()
    tokens = db_session.query(models.RefreshToken).filter(models.RefreshToken.user_id == user.id).all()
    for t in tokens:
        assert t.revoked_at is not None


def test_rate_limiting_sliding_window(client, db_session):
    # Repeatedly call an endpoint to trigger rate limits
    # Limit for /register is 5 requests per 10 mins by IP
    for i in range(5):
        resp = client.post("https://testserver/api/v1/auth/register", json={
            "email": f"rate{i}@uni.edu",
            "password": "Password123!",
            "full_name": "Rate User"
        })
        assert resp.status_code in (200, 422)

    # 6th attempt should block with 429
    resp_blocked = client.post("https://testserver/api/v1/auth/register", json={
        "email": "rate_blocked@uni.edu",
        "password": "Password123!",
        "full_name": "Rate User"
    })
    assert resp_blocked.status_code == 429
    assert "Too many requests" in resp_blocked.json()["detail"]


def test_audit_trail_and_revocation_on_logout(client, db_session):
    # Register and verify
    client.post("https://testserver/api/v1/auth/register", json={
        "email": "audit@uni.edu",
        "password": "Password123!",
        "full_name": "Audit User"
    })
    user = db_session.query(models.User).filter(models.User.email == "audit@uni.edu").first()
    user.is_verified = True
    db_session.commit()

    # Successful login
    client.post("https://testserver/api/v1/auth/login", data={
        "username": "audit@uni.edu",
        "password": "Password123!"
    })

    # Logout
    resp_logout = client.post("https://testserver/api/v1/auth/logout")
    assert resp_logout.status_code == 200
    assert client.cookies.get("refresh_token") is None

    # Verify audit logs in database
    logs = db_session.query(models.AuditLog).all()
    events = [log.event_type for log in logs]
    assert "registration" in events
    assert "login_success" in events
    assert "logout" in events
    # Ensure sensitive credentials are never stored in audit logs
    for log in logs:
        assert "Password123!" not in str(log.description)
        assert "token" not in str(log.description) or "issued" in str(log.description) or "revoked" in str(log.description)


def test_security_headers(client):
    # Verify that a request returns the configured security headers
    resp = client.get("https://testserver/api/v1/auth/google/client-id")
    assert resp.status_code == 200
    assert resp.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in resp.headers.get("Permissions-Policy", "")


def test_mfa_full_flow(client, db_session):
    import pyotp
    # 1. Register and verify user
    client.post("https://testserver/api/v1/auth/register", json={
        "email": "mfa_test@uni.edu",
        "password": "Password123!",
        "full_name": "Mfa User"
    })
    user = db_session.query(models.User).filter(models.User.email == "mfa_test@uni.edu").first()
    user.is_verified = True
    db_session.commit()

    # 2. Login to get access token
    resp = client.post("https://testserver/api/v1/auth/login", data={
        "username": "mfa_test@uni.edu",
        "password": "Password123!"
    })
    assert resp.status_code == 200
    access_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Enroll in MFA
    resp_enroll = client.post("https://testserver/api/v1/auth/mfa/enroll", headers=headers)
    assert resp_enroll.status_code == 200
    data = resp_enroll.json()
    assert "secret" in data
    assert "provisioning_uri" in data
    assert len(data["backup_codes"]) == 8
    secret = data["secret"]
    backup_codes = data["backup_codes"]

    # 4. Confirm MFA with code
    totp = pyotp.totp.TOTP(secret)
    code = totp.now()
    resp_confirm = client.post("https://testserver/api/v1/auth/mfa/confirm", headers=headers, json={"code": code})
    assert resp_confirm.status_code == 200
    assert resp_confirm.json()["message"] == "MFA enabled successfully."

    # 5. Try to login again - should require MFA
    resp_login2 = client.post("https://testserver/api/v1/auth/login", data={
        "username": "mfa_test@uni.edu",
        "password": "Password123!"
    })
    assert resp_login2.status_code == 200
    login_data = resp_login2.json()
    assert login_data["mfa_required"] is True
    mfa_token = login_data["mfa_token"]

    # 6. Verify MFA using incorrect code
    resp_verify_fail = client.post("https://testserver/api/v1/auth/mfa/verify", json={
        "mfa_token": mfa_token,
        "code": "000000"
    })
    assert resp_verify_fail.status_code == 401

    # 7. Verify MFA using correct TOTP code
    code = totp.now()
    resp_verify_success = client.post("https://testserver/api/v1/auth/mfa/verify", json={
        "mfa_token": mfa_token,
        "code": code
    })
    assert resp_verify_success.status_code == 200
    assert "access_token" in resp_verify_success.json()
    assert client.cookies.get("refresh_token") is not None

    # 8. Try login and verify with backup code
    resp_login3 = client.post("https://testserver/api/v1/auth/login", data={
        "username": "mfa_test@uni.edu",
        "password": "Password123!"
    })
    mfa_token3 = resp_login3.json()["mfa_token"]
    
    # Use backup code
    backup_code = backup_codes[0]
    resp_verify_backup = client.post("https://testserver/api/v1/auth/mfa/verify", json={
        "mfa_token": mfa_token3,
        "code": backup_code
    })
    assert resp_verify_backup.status_code == 200

    # Ensure backup code is single-use: try to use same code again
    resp_login4 = client.post("https://testserver/api/v1/auth/login", data={
        "username": "mfa_test@uni.edu",
        "password": "Password123!"
    })
    mfa_token4 = resp_login4.json()["mfa_token"]
    resp_verify_backup_again = client.post("https://testserver/api/v1/auth/mfa/verify", json={
        "mfa_token": mfa_token4,
        "code": backup_code
    })
    assert resp_verify_backup_again.status_code == 401

    # 9. Disable MFA
    new_access_token = resp_verify_backup.json()["access_token"]
    headers_new = {"Authorization": f"Bearer {new_access_token}"}
    
    # Try disable with wrong password
    resp_disable_fail = client.post("https://testserver/api/v1/auth/mfa/disable", headers=headers_new, json={"password": "WrongPassword!"})
    assert resp_disable_fail.status_code == 400

    # Disable with correct password
    resp_disable_success = client.post("https://testserver/api/v1/auth/mfa/disable", headers=headers_new, json={"password": "Password123!"})
    assert resp_disable_success.status_code == 200

    # Verify that login no longer requires MFA
    resp_login_final = client.post("https://testserver/api/v1/auth/login", data={
        "username": "mfa_test@uni.edu",
        "password": "Password123!"
    })
    assert resp_login_final.status_code == 200
    assert "access_token" in resp_login_final.json()
    assert not resp_login_final.json().get("mfa_required")



def test_active_sessions_and_revocation(client, db_session):
    # Register and verify user
    client.post("https://testserver/api/v1/auth/register", json={
        "email": "sessions_test@uni.edu",
        "password": "Password123!",
        "full_name": "Sessions User"
    })
    user = db_session.query(models.User).filter(models.User.email == "sessions_test@uni.edu").first()
    user.is_verified = True
    db_session.commit()

    # Login from client 1 (sets refresh token cookie)
    resp1 = client.post("https://testserver/api/v1/auth/login", data={
        "username": "sessions_test@uni.edu",
        "password": "Password123!"
    }, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
    token1 = resp1.json()["access_token"]

    # Get sessions
    resp_sess = client.get("https://testserver/api/v1/auth/sessions", headers={"Authorization": f"Bearer {token1}"})
    assert resp_sess.status_code == 200
    sessions = resp_sess.json()
    assert len(sessions) == 1
    assert sessions[0]["browser"] == "Chrome"
    assert sessions[0]["os"] == "Windows"
    assert sessions[0]["is_current"] is True
    session_id = sessions[0]["id"]

    # Revoke session
    resp_rev = client.delete(f"https://testserver/api/v1/auth/sessions/{session_id}", headers={"Authorization": f"Bearer {token1}"})
    assert resp_rev.status_code == 200

    # Verify session is revoked
    db_session.expire_all()
    token_db = db_session.query(models.RefreshToken).filter(models.RefreshToken.id == session_id).first()
    assert token_db.revoked_at is not None

    # Login again to test revoke other sessions
    resp2 = client.post("https://testserver/api/v1/auth/login", data={
        "username": "sessions_test@uni.edu",
        "password": "Password123!"
    }, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
    token2 = resp2.json()["access_token"]

    # Create another session in DB manually to simulate another device
    db_sess_other = models.RefreshToken(
        user_id=user.id,
        token_hash="fake_hash",
        expires_at=datetime.utcnow() + timedelta(days=5),
        device_info="Other UA",
        browser="Firefox",
        os="Linux",
        device_type="Desktop",
        last_activity=datetime.utcnow()
    )
    db_session.add(db_sess_other)
    db_session.commit()

    # Revoke others
    resp_rev_others = client.request("DELETE", "https://testserver/api/v1/auth/sessions/other", headers={"Authorization": f"Bearer {token2}"}, json={"password": "Password123!"})
    assert resp_rev_others.status_code == 200

    db_session.refresh(db_sess_other)
    assert db_sess_other.revoked_at is not None


def test_email_change_flow(client, db_session):
    # Register and verify user
    client.post("https://testserver/api/v1/auth/register", json={
        "email": "email_change@uni.edu",
        "password": "Password123!",
        "full_name": "Change User"
    })
    user = db_session.query(models.User).filter(models.User.email == "email_change@uni.edu").first()
    user.is_verified = True
    db_session.commit()

    # Login
    resp = client.post("https://testserver/api/v1/auth/login", data={
        "username": "email_change@uni.edu",
        "password": "Password123!"
    })
    token = resp.json()["access_token"]

    # Initiate email change
    resp_init = client.post("https://testserver/api/v1/auth/email/change", headers={"Authorization": f"Bearer {token}"}, json={
        "password": "Password123!",
        "new_email": "new_email@uni.edu"
    })
    assert resp_init.status_code == 200

    # Retrieve verification token from database (since we mock email printing)
    db_session.expire_all()
    user = db_session.query(models.User).filter(models.User.email == "email_change@uni.edu").first()
    assert user.pending_email == "new_email@uni.edu"
    assert user.email_change_token_hash is not None

    # Simulate click on confirm link: we need to find the token matching the hash
    test_token = "my_secret_email_change_token"
    test_hash = hashlib.sha256(test_token.encode()).hexdigest()
    user.email_change_token_hash = test_hash
    db_session.commit()

    # Confirm email change
    resp_confirm = client.post(f"https://testserver/api/v1/auth/email/confirm-change?token={test_token}")
    assert resp_confirm.status_code == 200
    assert "Email changed successfully" in resp_confirm.json()["message"]

    # Verify user email is updated in DB
    db_session.expire_all()
    user = db_session.query(models.User).filter(models.User.email == "new_email@uni.edu").first()
    assert user is not None
    assert user.pending_email is None


def test_password_change_and_account_deletion(client, db_session):
    # Register and verify
    client.post("https://testserver/api/v1/auth/register", json={
        "email": "delete_me@uni.edu",
        "password": "Password123!",
        "full_name": "Delete User"
    })
    user = db_session.query(models.User).filter(models.User.email == "delete_me@uni.edu").first()
    user.is_verified = True
    db_session.commit()

    # Login
    resp = client.post("https://testserver/api/v1/auth/login", data={
        "username": "delete_me@uni.edu",
        "password": "Password123!"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Change password
    resp_pwd = client.post("https://testserver/api/v1/auth/change-password-authenticated", headers=headers, json={
        "current_password": "Password123!",
        "new_password": "NewPassword123!"
    })
    assert resp_pwd.status_code == 200

    # Verify old password fails
    resp_login_old = client.post("https://testserver/api/v1/auth/login", data={
        "username": "delete_me@uni.edu",
        "password": "Password123!"
    })
    assert resp_login_old.status_code == 401

    # Verify new password login works
    resp_login_new = client.post("https://testserver/api/v1/auth/login", data={
        "username": "delete_me@uni.edu",
        "password": "NewPassword123!"
    })
    assert resp_login_new.status_code == 200
    token_new = resp_login_new.json()["access_token"]
    headers_new = {"Authorization": f"Bearer {token_new}"}

    # Delete account
    resp_del = client.post("https://testserver/api/v1/auth/delete-account", headers=headers_new, json={
        "password": "NewPassword123!"
    })
    assert resp_del.status_code == 200

    # Verify user no longer exists
    db_session.expire_all()
    user_del = db_session.query(models.User).filter(models.User.email == "delete_me@uni.edu").first()
    assert user_del is None

def test_email_normalization_and_validation(client):
    from app.routes.auth import normalize_email
    # Test normalization function
    assert normalize_email("  User@Uni.EDU  ") == "user@uni.edu"
    assert normalize_email(None) == ""
    assert normalize_email(123) == ""

    # Test registration with invalid email formats
    invalid_emails = [
        "abc",
        "abc@",
        "abc@com",
        "abc@gmail",
        "@@gmail.com",
        "user@",
        "user..name@gmail.com"
    ]
    for email in invalid_emails:
        resp = client.post("https://testserver/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Test User"
        })
        # Should be rejected with either 400 (custom validator) or 422 (Pydantic EmailStr validation)
        assert resp.status_code in (400, 422), f"Email {email} was not rejected"


@patch("app.routes.auth.verify_google_id_token")
@patch("requests.post")
def test_google_oauth_code_flow_success(mock_post, mock_verify, client, db_session):
    from app.config import settings
    
    # 1. Setup mock credentials
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock_client_id"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "mock_client_secret"), \
         patch.object(settings, "GOOGLE_REDIRECT_URI", "http://localhost:3000/login"):
         
        # Mock Google token endpoint response
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"id_token": "mock_google_id_token"}
        mock_post.return_value = mock_token_resp
        
        # Mock local token verification output
        mock_verify.return_value = {
            "email": "google_oauth_user@uni.edu",
            "email_verified": True,
            "name": "OAuth User"
        }
        
        # Call Google login route
        resp = client.post("https://testserver/api/v1/auth/google", json={
            "code": "mock_auth_code"
        })
        
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert client.cookies.get("refresh_token") is not None
        
        # Verify user was automatically registered and verified
        user = db_session.query(models.User).filter(models.User.email == "google_oauth_user@uni.edu").first()
        assert user is not None
        assert user.is_verified is True
        assert user.hashed_password is None


def test_google_login_missing_config(client):
    from app.config import settings
    # Test when credentials are not configured
    with patch.object(settings, "GOOGLE_CLIENT_ID", None), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", None), \
         patch.object(settings, "GOOGLE_REDIRECT_URI", None):
         
        # Client ID endpoint should return None
        resp_cid = client.get("https://testserver/api/v1/auth/google/client-id")
        assert resp_cid.status_code == 200
        assert resp_cid.json() == {"client_id": None, "redirect_uri": None}
        
        # Post should return 400 Bad Request
        resp_login = client.post("https://testserver/api/v1/auth/google", json={
            "code": "some_code"
        })
        assert resp_login.status_code == 400
        assert "not configured" in resp_login.json()["detail"]


@patch("requests.get")
@patch("jose.jwt.decode")
def test_verify_google_id_token_logic(mock_jwt_decode, mock_get):
    from app.routes.auth import verify_google_id_token
    from app.config import settings
    from fastapi import HTTPException
    
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock_client_id"):
        # Mock Google JWKs request
        mock_jwk_resp = MagicMock()
        mock_jwk_resp.status_code = 200
        mock_jwk_resp.json.return_value = {"keys": [{"kid": "1", "kty": "RSA", "n": "n", "e": "e"}]}
        mock_get.return_value = mock_jwk_resp
        
        # Mock jwt decode to return valid payload
        mock_jwt_decode.return_value = {
            "iss": "https://accounts.google.com",
            "aud": "mock_client_id",
            "exp": int(time.time()) + 3600,
            "email": "verified_user@uni.edu",
            "email_verified": True
        }
        
        claims = verify_google_id_token("mock_id_token")
        assert claims["email"] == "verified_user@uni.edu"
        
        # Test expired token logic
        mock_jwt_decode.return_value = {
            "iss": "https://accounts.google.com",
            "aud": "mock_client_id",
            "exp": int(time.time()) - 10,
            "email": "verified_user@uni.edu",
            "email_verified": True
        }
        with pytest.raises(HTTPException) as exc:
            verify_google_id_token("mock_id_token")
        assert exc.value.status_code == 400
        assert "expired" in exc.value.detail
        
        # Test unverified email logic
        mock_jwt_decode.return_value = {
            "iss": "https://accounts.google.com",
            "aud": "mock_client_id",
            "exp": int(time.time()) + 3600,
            "email": "verified_user@uni.edu",
            "email_verified": False
        }
        with pytest.raises(HTTPException) as exc:
            verify_google_id_token("mock_id_token")
        assert exc.value.status_code == 400
        assert "not verified" in exc.value.detail
