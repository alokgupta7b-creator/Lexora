import re
import secrets
import logging
import requests
import hashlib
import unicodedata
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db import models
from app.db.session import get_db
from app.schemas import schemas
from app.auth import security
from app.services.email import send_verification_email, send_password_reset_email, send_security_alert_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Regex for basic email format validation
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

# A valid dummy hash of the configured format to prevent base64 errors during timing dummy checks
DUMMY_HASH = security.get_password_hash("dummy_password")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class GoogleTokenRequest(BaseModel):
    code: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


def normalize_email(email: str) -> str:
    """Consistently trims, lowercases, and normalizes email format."""
    if not isinstance(email, str):
        return ""
    return unicodedata.normalize("NFKC", email.strip().lower())


def validate_email_format(email: str) -> None:
    """Validates email structure strictly, rejecting empty strings and double dots."""
    if not email or ".." in email or not re.match(EMAIL_REGEX, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format."
        )


def parse_user_agent(ua_string: str):
    """A lightweight regex parser for browser, OS, and device type."""
    browser = "Other"
    os_name = "Other"
    device_type = "Desktop"

    if not ua_string:
        return browser, os_name, device_type

    ua_lower = ua_string.lower()

    # Parse browser
    if "chrome" in ua_lower or "chromium" in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower:
        browser = "Safari"
    elif "edge" in ua_lower:
        browser = "Edge"
    elif "opera" in ua_lower:
        browser = "Opera"

    # Parse OS
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower or "mac_powerpc" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"

    # Parse device type
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device_type = "Mobile"
    elif "ipad" in ua_lower or "tablet" in ua_lower:
        device_type = "Tablet"

    return browser, os_name, device_type



def validate_password_strength(password: str) -> None:
    """Enforces 8-128 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special character."""
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )
    if len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot exceed 128 characters (denial of service limit)."
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter."
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter."
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number."
        )
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character."
        )


def log_audit(
    db: Session,
    event_type: str,
    email: Optional[str] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    description: Optional[str] = None
):
    """Inserts a secure append-only audit event into DB and server logs. Never logs raw secrets."""
    logger.info(
        f"[AUDIT] Event: {event_type} | Email: {email} | UserID: {user_id} | IP: {ip_address} | Description: {description}"
    )
    db_log = models.AuditLog(
        user_id=user_id,
        email=email,
        event_type=event_type,
        ip_address=ip_address,
        description=description,
        timestamp=datetime.utcnow()
    )
    db.add(db_log)
    db.commit()


def enforce_rate_limit(db: Session, key: str, endpoint: str, max_requests: int, window_seconds: int):
    """Applies IP/Account sliding-window rate throttling using database tables."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)

    # Invalidate and delete logs older than sliding window
    db.query(models.RateLimitLog).filter(
        models.RateLimitLog.key == key,
        models.RateLimitLog.endpoint == endpoint,
        models.RateLimitLog.timestamp < cutoff
    ).delete()
    db.commit()

    # Query active counts
    count = db.query(models.RateLimitLog).filter(
        models.RateLimitLog.key == key,
        models.RateLimitLog.endpoint == endpoint
    ).count()

    if count >= max_requests:
        log_audit(
            db=db,
            event_type="rate_limit_blocked",
            email=key.split(":")[-1] if "email:" in key else None,
            description=f"Rate limit exceeded on {endpoint}. Total requests: {count+1} (Limit: {max_requests} per {window_seconds}s)"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )

    # Log current request
    log_entry = models.RateLimitLog(key=key, endpoint=endpoint, timestamp=now)
    db.add(log_entry)
    db.commit()


@router.post("/register")
def register(request: Request, user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new researcher, enforcing verification while mitigating enumeration attacks."""
    ip = request.client.host if request.client else "unknown"
    
    # 1. Rate limiting by IP
    enforce_rate_limit(db, f"ip:{ip}", "/register", 5, 600)  # max 5 requests per 10 mins

    email_clean = normalize_email(user_in.email)
    validate_email_format(email_clean)

    # Validate password complexity
    validate_password_strength(user_in.password)

    # Check duplicates without disclosing account details
    existing_user = db.query(models.User).filter(models.User.email == email_clean).first()
    
    generic_success_msg = {
        "message": "Registration successful. A verification link has been sent to your email."
    }

    if existing_user:
        if security.settings.IS_AUTO_VERIFY_ENABLED:
            # In DEV_AUTO_VERIFY mode, update existing test user's password so dev can sign in immediately
            existing_user.hashed_password = security.get_password_hash(user_in.password)
            existing_user.is_verified = True
            existing_user.is_active = True
            existing_user.verification_token_hash = None
            db.commit()
            logger.info(f"[DEV] DEV_AUTO_VERIFY=true – account {email_clean} password updated.")
            return {"message": "Registration successful! Your account password has been updated. You can log in now."}

        # Mock registration email warning (prevent user enumeration while alerting the real account owner)
        logger.warning(
            f"\n[SMTP MOCK] Sending security warning to {email_clean}: A registration attempt was made with this email address, which is already registered. If this was you, please sign in or request a password reset.\n"
        )
        print(
            f"\n[SMTP MOCK] Sending security warning to {email_clean}: A registration attempt was made with this email address, which is already registered.\n"
        )
        log_audit(
            db=db,
            event_type="duplicate_registration_attempt",
            email=email_clean,
            ip_address=ip,
            description="Duplicate registration attempt blocked to prevent enumeration."
        )
        return generic_success_msg

    # Hash password using Argon2id Context
    hashed_pwd = security.get_password_hash(user_in.password)

    # First user becomes admin automatically to simplify bootstrap
    user_count = db.query(models.User).count()
    role = "admin" if user_count == 0 else "user"

    # Generate cryptographically secure verification token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token_expires = datetime.utcnow() + timedelta(hours=24)

    # In DEV_AUTO_VERIFY mode (if non-production), mark user verified immediately.
    auto_verified = security.settings.IS_AUTO_VERIFY_ENABLED

    db_user = models.User(
        email=email_clean,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        role=role,
        is_active=True,
        is_verified=auto_verified,
        verification_token_hash=None if auto_verified else token_hash,
        verification_token_expires=None if auto_verified else token_expires
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Seed user settings
    db_settings = models.UserSettings(user_id=db_user.id)
    db.add(db_settings)
    db.commit()

    if auto_verified:
        logger.info(f"[DEV] DEV_AUTO_VERIFY=true – account {email_clean} created and auto-verified.")
        print(f"\n[DEV] DEV_AUTO_VERIFY=true – account {email_clean} is ready. You can log in immediately.\n")
        log_audit(
            db=db,
            event_type="registration",
            email=email_clean,
            user_id=db_user.id,
            ip_address=ip,
            description="Researcher registered and auto-verified (DEV_AUTO_VERIFY mode)."
        )
        return {"message": "Registration successful! Your account is ready. You can log in now."}

    # Send real or mock verification email
    verify_link = f"{security.settings.FRONTEND_URL}/verify?token={raw_token}"
    send_verification_email(email_clean, verify_link)

    log_audit(
        db=db,
        event_type="registration",
        email=email_clean,
        user_id=db_user.id,
        ip_address=ip,
        description="Researcher registered successfully in unverified state."
    )

    return generic_success_msg


@router.post("/resend-verification")
def resend_verification(request: Request, payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Re-sends an expiring verification link to unverified users, throttling spam."""
    ip = request.client.host if request.client else "unknown"
    email_clean = normalize_email(payload.email)
    validate_email_format(email_clean)

    # Rate Limit: max 3 per 15 minutes by IP and by Account
    enforce_rate_limit(db, f"ip:{ip}", "/resend-verification", 3, 900)
    enforce_rate_limit(db, f"email:{email_clean}", "/resend-verification", 3, 900)

    generic_msg = {
        "message": "If this email is registered and unverified, a verification link has been sent."
    }

    user = db.query(models.User).filter(models.User.email == email_clean).first()
    if not user or user.is_verified or not user.is_active:
        log_audit(
            db=db,
            event_type="resend_verification_noop",
            email=email_clean,
            ip_address=ip,
            description="Resend request ignored (user missing, active, or verified) to prevent enumeration."
        )
        return generic_msg

    # Generate new token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    user.verification_token_hash = token_hash
    user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    db.commit()

    verify_link = f"{security.settings.FRONTEND_URL}/verify?token={raw_token}"
    send_verification_email(email_clean, verify_link)

    log_audit(
        db=db,
        event_type="verification_resent",
        email=email_clean,
        user_id=user.id,
        ip_address=ip,
        description="Verification link regenerated and sent."
    )

    return generic_msg


@router.get("/verify")
def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    """Verifies a user account using the SHA-256 hashed verification token."""
    ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(db, f"ip:{ip}", "/verify", 10, 900)  # max 10 requests per 15 mins

    incoming_hash = hashlib.sha256(token.encode()).hexdigest()

    user = db.query(models.User).filter(
        models.User.verification_token_hash == incoming_hash
    ).first()

    if not user or (user.verification_token_expires and datetime.utcnow() > user.verification_token_expires):
        log_audit(
            db=db,
            event_type="email_verification_failed",
            ip_address=ip,
            description="Attempted verification with invalid or expired token."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )

    # Activate
    user.is_verified = True
    user.verification_token_hash = None
    user.verification_token_expires = None
    db.commit()

    log_audit(
        db=db,
        event_type="email_verification",
        email=user.email,
        user_id=user.id,
        ip_address=ip,
        description="Email address verified successfully."
    )

    return {"message": "Email verified successfully."}


@router.post("/login", response_model=schemas.Token)
def login(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticates a user, rotates refresh tokens, and enforces rate-limiting lockouts."""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")
    
    # IP-based rate limiting
    enforce_rate_limit(db, f"ip:{ip}", "/login", 20, 60)

    email_clean = normalize_email(form_data.username)
    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = db.query(models.User).filter(models.User.email == email_clean).first()
    
    # Timing attack latency simulation if user doesn't exist
    if not user:
        security.verify_password("dummy_password", DUMMY_HASH)
        log_audit(db=db, event_type="login_failed", email=email_clean, ip_address=ip, description="Authentication failed: email not found.")
        raise invalid_credentials_exception

    # Brute-force rate limiting check (lock out for 15 minutes if failed attempts >= 5)
    if user.failed_login_attempts >= 5 and user.last_failed_login:
        lockout_end = user.last_failed_login + timedelta(minutes=15)
        if datetime.utcnow() < lockout_end:
            remaining_seconds = int((lockout_end - datetime.utcnow()).total_seconds())
            log_audit(db=db, event_type="lockout_blocked", email=email_clean, user_id=user.id, ip_address=ip, description=f"Locked user attempted sign in. Remaining lockout: {remaining_seconds}s.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Account locked. Try again in {remaining_seconds // 60} minutes."
            )

    # Check active status
    if not user.is_active:
        log_audit(db=db, event_type="login_failed_inactive", email=email_clean, user_id=user.id, ip_address=ip, description="Login block: account is inactive.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account."
        )

    # Verify hashed password (supports verification of old bcrypt and dual hashing upgrade to Argon2id)
    is_verified, updated_hash = security.verify_and_update_password(form_data.password, user.hashed_password)
    
    if not is_verified:
        # Increment failed login attempts
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.utcnow()
        db.commit()
        
        log_audit(db=db, event_type="login_failed", email=email_clean, user_id=user.id, ip_address=ip, description=f"Authentication failed: incorrect password. Attempt: {user.failed_login_attempts}/5")
        
        if user.failed_login_attempts >= 5:
            log_audit(db=db, event_type="account_lockout", email=email_clean, user_id=user.id, ip_address=ip, description="Account locked out for 15 minutes due to 5 consecutive login failures.")
            
        raise invalid_credentials_exception

    # Enforce email verification policy
    if not user.is_verified:
        log_audit(db=db, event_type="login_failed_unverified", email=email_clean, user_id=user.id, ip_address=ip, description="Login block: email not verified.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in."
        )

    # If the hash was bcrypt, save the new Argon2id hash dynamically
    if updated_hash:
        user.hashed_password = updated_hash
        logger.info(f"Dynamically upgraded password hash for {email_clean} to Argon2id.")

    # Reset failed login counts on successful auth
    user.failed_login_attempts = 0
    user.last_failed_login = None
    db.commit()

    if user.mfa_enabled:
        from jose import jwt
        mfa_token_expires = timedelta(minutes=5)
        mfa_payload = {
            "sub": user.email,
            "type": "mfa_temp",
            "exp": datetime.utcnow() + mfa_token_expires
        }
        mfa_token = jwt.encode(mfa_payload, security.settings.SECRET_KEY, algorithm=security.settings.ALGORITHM)
        
        log_audit(
            db=db,
            event_type="mfa_required",
            email=user.email,
            user_id=user.id,
            ip_address=ip,
            description="MFA step-up verification required."
        )
        return {"mfa_required": True, "mfa_token": mfa_token}

    # Generate access token (15 mins) and refresh token (7 days)
    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )

    refresh_token = secrets.token_urlsafe(32)
    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    refresh_expires = datetime.utcnow() + timedelta(days=7)

    browser, os_name, device_type = parse_user_agent(ua)

    # Store refresh token details
    db_refresh = models.RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=refresh_expires,
        device_info=ua[:255],
        ip_address=ip,
        browser=browser,
        os=os_name,
        device_type=device_type,
        last_activity=datetime.utcnow()
    )
    db.add(db_refresh)
    db.commit()

    # Set HttpOnly rotating refresh cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    log_audit(
        db=db,
        event_type="login_success",
        email=user.email,
        user_id=user.id,
        ip_address=ip,
        description="User logged in successfully. Access and rotating refresh token issued."
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=schemas.Token)
def refresh_session(response: Response, request: Request, db: Session = Depends(get_db)):
    """Verifies refresh token cookie, rotates it, and issues a new access token (re-use check is active)."""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")
    
    enforce_rate_limit(db, f"ip:{ip}", "/refresh", 60, 3600)  # max 60 per hour

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid refresh credentials."
        )

    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    token_entry = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == refresh_hash
    ).first()

    # 1. Reuse / Token Theft Detection
    if not token_entry:
        log_audit(
            db=db,
            event_type="refresh_token_unknown",
            ip_address=ip,
            description="Attempted session refresh with unrecognized token."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh credentials."
        )

    if token_entry.revoked_at is not None or datetime.utcnow() > token_entry.expires_at:
        # Token is already invalidated or expired.
        # If it was explicitly revoked, someone might be reusing it! Invalidate ALL user sessions!
        if token_entry.revoked_at is not None:
            db.query(models.RefreshToken).filter(
                models.RefreshToken.user_id == token_entry.user_id
            ).update({"revoked_at": datetime.utcnow()})
            db.commit()

            log_audit(
                db=db,
                event_type="refresh_token_reuse_detected",
                user_id=token_entry.user_id,
                ip_address=ip,
                description="Token reuse detected. Revoked all active user sessions to prevent theft."
            )
        else:
            log_audit(
                db=db,
                event_type="refresh_token_expired",
                user_id=token_entry.user_id,
                ip_address=ip,
                description="Session refresh blocked: token expired."
            )

        response.delete_cookie("refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again."
        )

    # 2. Get User & Verify Active status
    user = db.query(models.User).filter(models.User.id == token_entry.user_id).first()
    if not user or not user.is_active or not user.is_verified:
        log_audit(
            db=db,
            event_type="refresh_token_blocked_user",
            user_id=token_entry.user_id,
            ip_address=ip,
            description="Session refresh blocked: user account is locked or unverified."
        )
        response.delete_cookie("refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired."
        )

    # 3. Rotate Refresh Token (Invalidate old, issue new)
    token_entry.revoked_at = datetime.utcnow()
    db.commit()

    new_refresh = secrets.token_urlsafe(32)
    new_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
    new_expires = datetime.utcnow() + timedelta(days=7)

    browser, os_name, device_type = parse_user_agent(ua)

    db_new_refresh = models.RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=new_expires,
        device_info=ua[:255],
        ip_address=ip,
        browser=browser,
        os=os_name,
        device_type=device_type,
        last_activity=datetime.utcnow()
    )
    db.add(db_new_refresh)
    db.commit()

    # Re-issue access and refresh cookie
    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    log_audit(
        db=db,
        event_type="token_refreshed",
        email=user.email,
        user_id=user.id,
        ip_address=ip,
        description="Session rotated successfully. Issued new credentials."
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    """Revokes the current refresh session and cleans cookies."""
    ip = request.client.host if request.client else "unknown"
    refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        token_entry = db.query(models.RefreshToken).filter(
            models.RefreshToken.token_hash == refresh_hash
        ).first()

        if token_entry and token_entry.revoked_at is None:
            token_entry.revoked_at = datetime.utcnow()
            db.commit()
            log_audit(
                db=db,
                event_type="logout",
                user_id=token_entry.user_id,
                ip_address=ip,
                description="Session revoked successfully."
            )

    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully."}


@router.post("/logout-all")
def logout_all(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Revokes all refresh tokens in DB for the active user, signing them out of all devices."""
    ip = request.client.host if request.client else "unknown"

    # Revoke all tokens
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == current_user.id,
        models.RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": datetime.utcnow()})
    db.commit()

    response.delete_cookie("refresh_token")

    log_audit(
        db=db,
        event_type="token_revocation",
        email=current_user.email,
        user_id=current_user.id,
        ip_address=ip,
        description="Revoked all active refresh sessions (logout from all devices)."
    )

    return {"message": "Successfully logged out from all devices."}


@router.get("/google/client-id")
def get_google_client_id():
    """Returns the Google Client ID and redirect URI configured on the server, or nulls if unconfigured."""
    if not security.settings.GOOGLE_CLIENT_ID or not security.settings.GOOGLE_CLIENT_SECRET or not security.settings.GOOGLE_REDIRECT_URI:
        return {"client_id": None, "redirect_uri": None}
    return {
        "client_id": security.settings.GOOGLE_CLIENT_ID,
        "redirect_uri": security.settings.GOOGLE_REDIRECT_URI
    }


def verify_google_id_token(id_token: str) -> dict:
    """Decodes and verifies a Google ID token locally using signing certificates fetched from Google."""
    from jose import jwt
    import requests
    # Fetch public certs
    try:
        certs_resp = requests.get("https://www.googleapis.com/oauth2/v3/certs", timeout=5)
        if certs_resp.status_code != 200:
            raise Exception("Failed to retrieve public certificates from Google.")
        jwks = certs_resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch Google public certs: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to contact Google identity providers to retrieve public keys."
        )

    # Decode and verify signature, aud, exp
    try:
        claims = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=security.settings.GOOGLE_CLIENT_ID,
            options={"verify_iss": False}
        )
    except Exception as e:
        logger.error(f"Google token signature/claims verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token validation failed."
        )

    # Validate issuer manually
    iss = claims.get("iss", "")
    if iss not in ["accounts.google.com", "https://accounts.google.com"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token issuer verification failed."
        )

    # Validate expiration manually just to be sure
    exp = claims.get("exp")
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token has no expiration claim."
        )
    try:
        if time.time() > int(exp):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token has expired."
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token expiration format."
        )

    # Validate email_verified
    email = normalize_email(claims.get("email", ""))
    validate_email_format(email)
    email_verified = claims.get("email_verified")

    if not email_verified or email_verified in ("false", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified."
        )

    return claims


@router.post("/google", response_model=schemas.Token)
def google_login(
    response: Response,
    request: Request,
    payload: GoogleTokenRequest,
    db: Session = Depends(get_db)
):
    """Hardened Google OIDC login: exchanges authorization code, verifies token locally, and establishes session."""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")

    enforce_rate_limit(db, f"ip:{ip}", "/google", 20, 60)

    # Check configuration
    if not security.settings.GOOGLE_CLIENT_ID or not security.settings.GOOGLE_CLIENT_SECRET or not security.settings.GOOGLE_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Authentication is not configured on this server."
        )

    code = payload.code.strip()

    # 1. Exchange authorization code for tokens
    google_token_url = "https://oauth2.googleapis.com/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "code": code,
        "client_id": security.settings.GOOGLE_CLIENT_ID,
        "client_secret": security.settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": security.settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    try:
        token_resp = requests.post(google_token_url, data=data, headers=headers, timeout=10)
        if token_resp.status_code != 200:
            logger.error(f"Google token exchange failed: {token_resp.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google code exchange failed or invalid authorization code."
            )
        token_data = token_resp.json()
        id_token = token_data.get("id_token")
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No id_token returned from Google code exchange."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google token exchange request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code with Google."
        )

    # 2. Local token verification (signature, aud, iss, exp, email_verified)
    claims = verify_google_id_token(id_token)
    email = normalize_email(claims.get("email", ""))
    
    # 3. Retrieve or register user (automatic linking)
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Create Google SSO user (is_verified = True automatically since Google checked email)
        user = models.User(
            email=email,
            hashed_password=None,
            full_name=claims.get("name", "Google Scholar"),
            role="user",
            is_active=True,
            is_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Settings
        db_settings = models.UserSettings(user_id=user.id)
        db.add(db_settings)
        db.commit()
        
        log_audit(
            db=db,
            event_type="registration",
            email=email,
            user_id=user.id,
            ip_address=ip,
            description="Registered user automatically via Google OIDC."
        )
    else:
        # Automatically verify existing unverified account if they authenticate via verified Google SSO
        if not user.is_verified:
            user.is_verified = True
            db.commit()
            log_audit(db=db, event_type="email_verification", email=email, user_id=user.id, ip_address=ip, description="Account verified via Google OIDC linking.")

        log_audit(
            db=db,
            event_type="login_success",
            email=email,
            user_id=user.id,
            ip_address=ip,
            description="Google login successful. Identity matched."
        )

    if user.mfa_enabled:
        from jose import jwt
        mfa_token_expires = timedelta(minutes=5)
        mfa_payload = {
            "sub": user.email,
            "type": "mfa_temp",
            "exp": datetime.utcnow() + mfa_token_expires
        }
        mfa_token = jwt.encode(mfa_payload, security.settings.SECRET_KEY, algorithm=security.settings.ALGORITHM)
        
        log_audit(
            db=db,
            event_type="mfa_required",
            email=user.email,
            user_id=user.id,
            ip_address=ip,
            description="MFA step-up verification required for Google SSO."
        )
        return {"mfa_required": True, "mfa_token": mfa_token}

    # Generate access token and refresh token
    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )

    refresh_token = secrets.token_urlsafe(32)
    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    refresh_expires = datetime.utcnow() + timedelta(days=7)

    browser, os_name, device_type = parse_user_agent(ua)

    db_refresh = models.RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=refresh_expires,
        device_info=ua[:255],
        ip_address=ip,
        browser=browser,
        os=os_name,
        device_type=device_type,
        last_activity=datetime.utcnow()
    )
    db.add(db_refresh)
    db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Generates password reset links, preventing user enumeration by returning generic success."""
    ip = request.client.host if request.client else "unknown"
    email_clean = normalize_email(payload.email)
    validate_email_format(email_clean)

    # Rate Limit: max 3 per 15 minutes by IP and Email
    enforce_rate_limit(db, f"ip:{ip}", "/forgot-password", 3, 900)
    enforce_rate_limit(db, f"email:{email_clean}", "/forgot-password", 3, 900)

    generic_success_msg = {
        "message": "If your email is registered, you will receive a password reset link."
    }

    user = db.query(models.User).filter(models.User.email == email_clean).first()
    
    if user:
        reset_token = secrets.token_urlsafe(32)
        reset_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        
        user.password_reset_token_hash = reset_hash
        user.password_reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        reset_link = f"{security.settings.FRONTEND_URL}/reset-password?token={reset_token}"
        send_password_reset_email(email_clean, reset_link)
        
        log_audit(
            db=db,
            event_type="password_reset_requested",
            email=email_clean,
            user_id=user.id,
            ip_address=ip,
            description="Password reset token issued and printed."
        )
    else:
        # Mock registration email warning to keep log trace consistent
        logger.warning(
            f"\n[SMTP MOCK] Attempted password reset for unregistered email: {email_clean}.\n"
        )
        print(
            f"\n[SMTP MOCK] Attempted password reset for unregistered email: {email_clean}.\n"
        )
        log_audit(
            db=db,
            event_type="password_reset_requested_unregistered",
            email=email_clean,
            ip_address=ip,
            description="Password reset attempt on unregistered email address."
        )

    return generic_success_msg


@router.post("/reset-password")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Resets user password with valid expiring reset token (invalidating token on success)."""
    ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(db, f"ip:{ip}", "/reset-password", 5, 900)  # max 5 requests per 15 mins

    incoming_hash = hashlib.sha256(payload.token.encode()).hexdigest()

    user = db.query(models.User).filter(
        models.User.password_reset_token_hash == incoming_hash
    ).first()

    if not user or (user.password_reset_token_expires and datetime.utcnow() > user.password_reset_token_expires):
        log_audit(
            db=db,
            event_type="password_reset_failed",
            ip_address=ip,
            description="Attempted reset with invalid or expired token."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )

    # Enforce password policies
    validate_password_strength(payload.password)

    # Hash and clear reset token (ensuring single use)
    user.hashed_password = security.get_password_hash(payload.password)
    user.password_reset_token_hash = None
    user.password_reset_token_expires = None
    db.commit()

    log_audit(
        db=db,
        event_type="password_reset_completed",
        email=user.email,
        user_id=user.id,
        ip_address=ip,
        description="Password updated successfully. Reset token cleared."
    )

    return {"message": "Password reset successfully."}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(security.get_current_user)):
    """Returns the authenticated user details."""
    return current_user


# --- Multi-Factor Authentication (MFA) Endpoints ---

@router.post("/mfa/enroll")
def mfa_enroll(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Enrolls a user in MFA, returning secret, provisioning URI, and recovery codes."""
    import pyotp
    
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled on this account."
        )
        
    secret = pyotp.random_base32()
    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    backup_hashes = [hashlib.sha256(code.encode()).hexdigest() for code in backup_codes]
    
    current_user.mfa_secret = secret
    current_user.mfa_backup_codes_hash = backup_hashes
    db.commit()
    
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="Lexora"
    )
    
    log_audit(
        db=db,
        event_type="mfa_enroll_initiated",
        email=current_user.email,
        user_id=current_user.id,
        description="MFA enrollment initiated. Secret and backup codes generated."
    )
    
    return {
        "secret": secret,
        "provisioning_uri": uri,
        "backup_codes": backup_codes
    }


@router.post("/mfa/confirm")
def mfa_confirm(
    payload: schemas.MfaConfirmRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Verifies the first TOTP code to toggle mfa_enabled = True."""
    import pyotp
    
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA has not been enrolled. Call enroll first."
        )
        
    totp = pyotp.totp.TOTP(current_user.mfa_secret)
    if not totp.verify(payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )
        
    current_user.mfa_enabled = True
    db.commit()
    
    log_audit(
        db=db,
        event_type="mfa_enabled",
        email=current_user.email,
        user_id=current_user.id,
        description="MFA successfully enabled on account."
    )
    
    return {"message": "MFA enabled successfully."}


@router.post("/mfa/verify", response_model=schemas.Token)
def mfa_verify(
    response: Response,
    request: Request,
    payload: schemas.MfaVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verifies TOTP or backup code to complete step-up MFA login."""
    import pyotp
    from jose import jwt
    
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")
    
    try:
        decoded = jwt.decode(
            payload.mfa_token,
            security.settings.SECRET_KEY,
            algorithms=[security.settings.ALGORITHM]
        )
        email = decoded.get("sub")
        token_type = decoded.get("type")
        if not email or token_type != "mfa_temp":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired MFA session token."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA session token."
        )
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive."
        )
        
    is_valid = False
    
    # 1. Try TOTP code verification
    if user.mfa_secret:
        totp = pyotp.totp.TOTP(user.mfa_secret)
        is_valid = totp.verify(payload.code)
        
    # 2. Try backup codes verification
    if not is_valid and user.mfa_backup_codes_hash:
        code_hash = hashlib.sha256(payload.code.upper().encode()).hexdigest()
        if code_hash in user.mfa_backup_codes_hash:
            is_valid = True
            # Consume single-use backup code
            new_hashes = [h for h in user.mfa_backup_codes_hash if h != code_hash]
            user.mfa_backup_codes_hash = new_hashes
            db.commit()
            
            log_audit(
                db=db,
                event_type="mfa_backup_code_used",
                email=user.email,
                user_id=user.id,
                ip_address=ip,
                description="MFA authenticated successfully via backup code."
            )
            
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code."
        )
        
    # Standard Login Success Code Path:
    user.failed_login_attempts = 0
    user.last_failed_login = None
    db.commit()

    # Generate access token (15 mins) and refresh token (7 days)
    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )

    refresh_token = secrets.token_urlsafe(32)
    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    refresh_expires = datetime.utcnow() + timedelta(days=7)

    browser, os_name, device_type = parse_user_agent(ua)

    # Store refresh token details
    db_refresh = models.RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=refresh_expires,
        device_info=ua[:255],
        ip_address=ip,
        browser=browser,
        os=os_name,
        device_type=device_type,
        last_activity=datetime.utcnow()
    )
    db.add(db_refresh)
    db.commit()

    # Set HttpOnly rotating refresh cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    log_audit(
        db=db,
        event_type="login_success",
        email=user.email,
        user_id=user.id,
        ip_address=ip,
        description="MFA authentication successful. Access and rotating refresh token issued."
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/mfa/disable")
def mfa_disable(
    payload: schemas.MfaDisableRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Disables MFA for the user's account after password verification."""
    if current_user.hashed_password:
        if not security.verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password."
            )
            
    current_user.mfa_secret = None
    current_user.mfa_enabled = False
    current_user.mfa_backup_codes_hash = None
    db.commit()
    
    log_audit(
        db=db,
        event_type="mfa_disabled",
        email=current_user.email,
        user_id=current_user.id,
        description="MFA disabled on account."
    )
    
    return {"message": "MFA disabled successfully."}


# --- Active Session Management Endpoints ---

@router.get("/sessions", response_model=List[schemas.SessionResponse])
def get_sessions(
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all active login sessions for the authenticated user."""
    sessions = db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == current_user.id,
        models.RefreshToken.expires_at > datetime.utcnow(),
        models.RefreshToken.revoked_at.is_(None)
    ).all()
    
    current_refresh = request.cookies.get("refresh_token")
    current_hash = hashlib.sha256(current_refresh.encode()).hexdigest() if current_refresh else None
    
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "browser": s.browser,
            "os": s.os,
            "device_type": s.device_type,
            "ip_address": s.ip_address,
            "created_at": s.created_at,
            "last_activity": s.last_activity or s.created_at,
            "expires_at": s.expires_at,
            "is_current": (current_hash is not None and s.token_hash == current_hash)
        })
    return result


@router.delete("/sessions/other")
def revoke_other_sessions(
    request: Request,
    payload: schemas.SessionOtherRevokeRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes all other active sessions for the user after password verification."""
    ip = request.client.host if request.client else "unknown"
    
    if current_user.hashed_password:
        if not security.verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password."
            )
            
    current_refresh = request.cookies.get("refresh_token")
    current_hash = hashlib.sha256(current_refresh.encode()).hexdigest() if current_refresh else None
    
    query = db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == current_user.id,
        models.RefreshToken.revoked_at.is_(None)
    )
    if current_hash:
        query = query.filter(models.RefreshToken.token_hash != current_hash)
        
    query.update({"revoked_at": datetime.utcnow()}, synchronize_session=False)
    db.commit()
    
    log_audit(
        db=db,
        event_type="other_sessions_revoked",
        email=current_user.email,
        user_id=current_user.id,
        ip_address=ip,
        description="All other active user sessions were revoked."
    )
    
    return {"message": "All other sessions revoked successfully."}


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: int,
    request: Request,
    response: Response,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes a specific active session."""
    ip = request.client.host if request.client else "unknown"
    
    session = db.query(models.RefreshToken).filter(
        models.RefreshToken.id == session_id,
        models.RefreshToken.user_id == current_user.id,
        models.RefreshToken.revoked_at.is_(None)
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active session not found."
        )
        
    session.revoked_at = datetime.utcnow()
    db.commit()
    
    current_refresh = request.cookies.get("refresh_token")
    current_hash = hashlib.sha256(current_refresh.encode()).hexdigest() if current_refresh else None
    if current_hash and session.token_hash == current_hash:
        response.delete_cookie("refresh_token")
        
    log_audit(
        db=db,
        event_type="session_revoked",
        email=current_user.email,
        user_id=current_user.id,
        ip_address=ip,
        description=f"Session {session_id} was revoked."
    )
    
    return {"message": "Session revoked successfully."}


# --- Verified Email Change Endpoints ---

@router.post("/email/change")
def initiate_email_change(
    payload: schemas.EmailChangeRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Initiates secure email swapping process with double email checks."""
    if current_user.hashed_password:
        if not security.verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password."
            )
            
    new_email_clean = normalize_email(payload.new_email)
    validate_email_format(new_email_clean)
        
    existing = db.query(models.User).filter(models.User.email == new_email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email address is already in use by another account."
        )
        
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    current_user.pending_email = new_email_clean
    current_user.email_change_token_hash = token_hash
    current_user.email_change_token_expires = datetime.utcnow() + timedelta(hours=24)
    db.commit()
    
    # Send mock emails to both old and new addresses
    logger.warning(
        f"\n[SMTP MOCK] Sending security warning to old email {current_user.email}: A request has been made to change your email address to {new_email_clean}. If this wasn't you, secure your account immediately.\n"
    )
    print(
        f"\n[SMTP MOCK] Sending security warning to old email {current_user.email}: A request has been made to change your email address to {new_email_clean}.\n"
    )
    
    confirm_link = f"http://localhost:3000/confirm-email-change?token={raw_token}"
    logger.info(
        f"\n[SMTP MOCK] Sending email change confirmation to new email {new_email_clean}\nConfirm Link: {confirm_link}\n"
    )
    print(
        f"\n[SMTP MOCK] Sending email change confirmation to new email {new_email_clean}\nConfirm Link: {confirm_link}\n"
    )
    
    log_audit(
        db=db,
        event_type="email_change_initiated",
        email=current_user.email,
        user_id=current_user.id,
        description=f"Initiated email change to {new_email_clean}."
    )
    
    return {"message": "Verification link sent to your new email. Please verify it to complete the change."}


@router.post("/email/confirm-change")
def confirm_email_change(
    request: Request,
    response: Response,
    token: Optional[str] = None,
    payload: Optional[schemas.EmailChangeConfirmRequest] = None,
    db: Session = Depends(get_db)
):
    """Confirms email swap using the unique urlsafe token and revokes all active sessions."""
    ip = request.client.host if request.client else "unknown"
    
    incoming_token = token
    if not incoming_token and payload:
        incoming_token = payload.token
        
    if not incoming_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation token is required."
        )
        
    token_hash = hashlib.sha256(incoming_token.encode()).hexdigest()
    user = db.query(models.User).filter(
        models.User.email_change_token_hash == token_hash
    ).first()
    
    if not user or (user.email_change_token_expires and datetime.utcnow() > user.email_change_token_expires):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email change token."
        )
        
    old_email = user.email
    new_email = user.pending_email
    
    user.email = new_email
    user.pending_email = None
    user.email_change_token_hash = None
    user.email_change_token_expires = None
    
    # Revoke all sessions
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user.id,
        models.RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": datetime.utcnow()}, synchronize_session=False)
    db.commit()
    
    response.delete_cookie("refresh_token")
    
    log_audit(
        db=db,
        event_type="email_change_confirmed",
        email=new_email,
        user_id=user.id,
        ip_address=ip,
        description=f"Email successfully changed from {old_email} to {new_email}. All sessions revoked."
    )
    
    return {"message": "Email changed successfully. All sessions revoked. Please log in again."}


# --- Account Security Settings Endpoints ---

@router.post("/change-password-authenticated")
def change_password_authenticated(
    payload: schemas.ChangePasswordAuthenticatedRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Changes password for an authenticated user after current password verification."""
    if current_user.hashed_password:
        if not security.verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password."
            )
            
    validate_password_strength(payload.new_password)
    
    current_user.hashed_password = security.get_password_hash(payload.new_password)
    db.commit()
    
    log_audit(
        db=db,
        event_type="password_changed",
        email=current_user.email,
        user_id=current_user.id,
        description="Password updated successfully for authenticated user."
    )
    
    return {"message": "Password changed successfully."}


@router.post("/delete-account")
def delete_account(
    payload: schemas.DeleteAccountRequest,
    response: Response,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently deletes the user's account after password verification."""
    if current_user.hashed_password:
        if not security.verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password."
            )
            
    user_id = current_user.id
    email = current_user.email
    
    db.delete(current_user)
    db.commit()
    
    response.delete_cookie("refresh_token")
    
    log_audit(
        db=db,
        event_type="account_deleted",
        email=email,
        user_id=user_id,
        description="User account permanently deleted."
    )
    
    return {"message": "Account deleted successfully."}
