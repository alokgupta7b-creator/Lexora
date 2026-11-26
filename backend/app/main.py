import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.session import engine, Base
from app.routes import auth, documents, admin

# Perform database table bootstrapping and migrations on startup
def run_db_migrations():
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    
    # 1. Create any missing tables (refresh_tokens, audit_logs, rate_limit_logs, etc.)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database table bootstrap skipped or failed: {str(e)}. Ensure DB is running.")

    # 2. Check and migrate the users and refresh_tokens tables incrementally (SQLite support)
    try:
        columns_users = [col["name"] for col in inspector.get_columns("users")]
        columns_refresh = [col["name"] for col in inspector.get_columns("refresh_tokens")]
        
        with engine.begin() as conn:
            # users columns
            if "is_verified" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0;"))
            if "verification_token" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR;"))
            if "verification_token_expires" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN verification_token_expires DATETIME;"))
            if "password_reset_token" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_token VARCHAR;"))
            if "password_reset_token_expires" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_token_expires DATETIME;"))
            if "failed_login_attempts" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;"))
            if "last_failed_login" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_failed_login DATETIME;"))
            if "verification_token_hash" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN verification_token_hash VARCHAR;"))
            if "password_reset_token_hash" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_token_hash VARCHAR;"))
            if "mfa_secret" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN mfa_secret VARCHAR;"))
            if "mfa_enabled" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT 0;"))
            if "mfa_backup_codes_hash" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN mfa_backup_codes_hash JSON;"))
            if "pending_email" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN pending_email VARCHAR;"))
            if "email_change_token_hash" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_change_token_hash VARCHAR;"))
            if "email_change_token_expires" not in columns_users:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_change_token_expires DATETIME;"))
                
            # refresh_tokens columns
            if "last_activity" not in columns_refresh:
                conn.execute(text("ALTER TABLE refresh_tokens ADD COLUMN last_activity DATETIME;"))
            if "browser" not in columns_refresh:
                conn.execute(text("ALTER TABLE refresh_tokens ADD COLUMN browser VARCHAR;"))
            if "os" not in columns_refresh:
                conn.execute(text("ALTER TABLE refresh_tokens ADD COLUMN os VARCHAR;"))
            if "device_type" not in columns_refresh:
                conn.execute(text("ALTER TABLE refresh_tokens ADD COLUMN device_type VARCHAR;"))
            
            print("Incremental Migration: Checked and updated users and refresh_tokens schemas.")
    except Exception as e:
        print(f"Incremental enterprise column migration skipped or failed: {str(e)}.")

run_db_migrations()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Linguistic Profiling, AI Risk Score, Readability analysis & semantic paper rephraser.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Dynamic CORS Setup from Environment Settings
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Telemetry Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    allowed_connect = " ".join(origins)
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self' {allowed_connect}; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        f"connect-src 'self' {allowed_connect} https://oauth2.googleapis.com;"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response

# Mount Sub-Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

@app.get("/")
def get_root():
    """Service health check endpoint."""
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_docs_path": "/docs"
    }
