from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.db import models

# Password context for hashing using argon2 (Argon2id) as primary, bcrypt as fallback
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_password_hash(password: str) -> str:
    if len(password) > 128:
        raise ValueError("Password exceeds maximum allowed length of 128 characters.")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password) > 128:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def verify_and_update_password(plain_password: str, hashed_password: str) -> tuple[bool, Optional[str]]:
    """
    Verifies password and checks if the hash needs to be updated (e.g. from bcrypt to argon2).
    Returns (is_verified, updated_hash_or_none).
    """
    if len(plain_password) > 128:
        return False, None
    return pwd_context.verify_and_update(plain_password, hashed_password)

def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in."
        )
    return user

def get_current_admin(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user
