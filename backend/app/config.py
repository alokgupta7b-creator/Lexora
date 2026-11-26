import os
import secrets
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lexora: Research Paper AI Risk Analyzer, Rephraser & Humanizer"
    API_V1_STR: str = "/api/v1"
    
    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ai_detector_local.db")
    
    # Caching
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    REPORTS_DIR: str = os.getenv("REPORTS_DIR", "reports")
    
    # AWS S3 (Ready Architecture)
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET_NAME: Optional[str] = os.getenv("AWS_S3_BUCKET_NAME")
    USE_S3: bool = False
    
    # AI API keys (OpenAI / HuggingFace fallback integration)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    HF_API_KEY: Optional[str] = os.getenv("HF_API_KEY")
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI")

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, gemini, anthropic, huggingface, local
    LLM_MODEL: Optional[str] = os.getenv("LLM_MODEL")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    HUGGINGFACE_API_KEY: Optional[str] = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_API_KEY")
    LLM_BASE_URL: Optional[str] = os.getenv("LLM_BASE_URL")
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "30.0"))
    LLM_TEMPERATURE: Optional[float] = None
    LLM_TOP_P: float = float(os.getenv("LLM_TOP_P", "0.95"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    PROMPT_VERSION: str = os.getenv("PROMPT_VERSION", "v1")

    # ── Email / SMTP ──────────────────────────────────────────────────────────
    # Set SMTP_HOST + SMTP_USERNAME + SMTP_PASSWORD to enable real email sending.
    # Leave blank to stay in mock-mode (links printed to console only).
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")         # e.g. smtp.gmail.com
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))        # 587 = STARTTLS, 465 = SSL
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")  # your full email address
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")  # app password or account password
    SMTP_FROM: str = os.getenv("SMTP_FROM", "no-reply@lexora.app")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    # Environment setup (development, staging, production)
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost")

    # ── Developer / Testing helpers ───────────────────────────────────────────
    # When DEV_AUTO_VERIFY=true, newly registered accounts are automatically
    # marked as verified so you can log in immediately without email.
    # NEVER enable this in production.
    DEV_AUTO_VERIFY: bool = os.getenv("DEV_AUTO_VERIFY", "false").lower() == "true"

    @property
    def IS_AUTO_VERIFY_ENABLED(self) -> bool:
        """Returns True only if DEV_AUTO_VERIFY is requested AND environment is NOT production."""
        if self.ENVIRONMENT.lower() in ["production", "prod"]:
            return False
        return self.DEV_AUTO_VERIFY

    # Frontend base URL used to build verification / reset links.
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    class Config:
        case_sensitive = True

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
