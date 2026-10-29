import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_database_url() -> str:
    # Use configured database URL
    return settings.DATABASE_URL

# Create engine
database_url = get_database_url()
is_sqlite = database_url.startswith("sqlite")

try:
    if is_sqlite:
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False}
        )
    else:
        # PostgreSQL engine
        engine = create_engine(
            database_url,
            connect_args={"connect_timeout": 2},
            pool_pre_ping=True,
            pool_recycle=300
        )
        # Test connection
        with engine.connect() as conn:
            pass
        logger.info("Successfully connected to PostgreSQL database.")
except Exception as e:
    logger.warning(
        f"Could not connect to PostgreSQL at {database_url} ({e}). "
        "Falling back to local SQLite dev_fallback.db for testing/development. "
        "Please ensure PostgreSQL is installed and running with pgvector for production."
    )
    database_url = "sqlite:///./dev_fallback.db"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
