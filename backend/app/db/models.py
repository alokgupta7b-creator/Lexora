import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for Google Auth users
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")  # 'user' or 'admin'
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_token_hash = Column(String, nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_token_hash = Column(String, nullable=True)
    password_reset_token_expires = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # MFA Columns
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_backup_codes_hash = Column(JSON, nullable=True)
    
    # Email Change Columns
    pending_email = Column(String, nullable=True)
    email_change_token_hash = Column(String, nullable=True)
    email_change_token_expires = Column(DateTime, nullable=True)

    # Relationships
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    history = relationship("History", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", uselist=False, back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'pdf', 'docx', 'txt'
    raw_text = Column(Text, nullable=False)
    parsed_sections = Column(JSON, nullable=True)  # JSON dictionary of section contents
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="documents")
    analysis_results = relationship("AnalysisResult", back_populates="document", uselist=False, cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="document", cascade="all, delete-orphan")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False)
    overall_score = Column(Float, nullable=False)  # 0 to 100 risk score
    section_scores = Column(JSON, nullable=True)   # Score for Abstract, Intro, etc.
    readability_scores = Column(JSON, nullable=True) # Flesch, Gunning Fog, etc.
    risk_details = Column(JSON, nullable=True)     # Detailed sentence-wise, paragraph-wise risks
    academic_quality_score = Column(Float, nullable=True)
    publication_readiness_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="analysis_results")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    report_path = Column(String, nullable=False)
    report_type = Column(String, nullable=False)  # 'pdf', 'docx', 'txt'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="reports")

class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String, nullable=False)  # 'upload', 'analyze', 'rephrase', 'humanize', 'report_export'
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="history")

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    preference_theme = Column(String, default="dark")  # 'light' or 'dark'
    default_rephrase_mode = Column(String, default="Academic")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="settings")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    device_info = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    last_activity = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)
    device_type = Column(String, nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    email = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class RateLimitLog(Base):
    __tablename__ = "rate_limit_logs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, index=True, nullable=False)
    endpoint = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

