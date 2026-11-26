from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
from app.config import settings

# Create DB Engine
try:
    if settings.DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
    else:
        # Check connection before proceeding
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        with engine.connect() as conn:
            pass
except Exception as e:
    print(f"PostgreSQL connection failed: {e}. Falling back to SQLite for local development.")
    sqlite_url = "sqlite:///./ai_detector_local.db"
    engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False}
    )


# Session Local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base
Base = declarative_base()

# Dependency to get DB session
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
