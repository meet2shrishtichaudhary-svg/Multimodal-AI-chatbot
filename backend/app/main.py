import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.core.middleware import (
    SecurityHeadersMiddleware,
    CorrelationIdAndLoggingMiddleware,
    RateLimitMiddleware
)
from app.db.session import engine, Base
from app.db import models  # Ensures models are imported for metadata registration
from app.routers import health, conversations, chat, uploads, documents, search, audio, images, auth, memory, feedback, jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mm_chatbot")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure upload dir and database tables exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Initialized uploads storage directory at: {settings.UPLOAD_DIR}")

    # Initialize PostgreSQL pgvector extension if PostgreSQL is active
    try:
        bind = engine
        if bind.dialect.name == "postgresql":
            with bind.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("Successfully enabled or verified 'vector' extension in PostgreSQL.")
    except Exception as e:
        logger.warning(f"Could not enable pgvector extension automatically ({e}). If using PostgreSQL, run 'CREATE EXTENSION IF NOT EXISTS vector;'")

    # Create tables
    try:
        Base.metadata.create_all(bind=engine)
        # Ensure user_id column exists on existing tables for SQLite or unmigrated databases
        with engine.connect() as conn:
            for tbl in ["conversations", "knowledge_documents", "document_workspaces"]:
                try:
                    conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN user_id VARCHAR(36);"))
                    conn.commit()
                except Exception:
                    pass
        logger.info("Database schema validated and initialized successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full-stack Multimodal AI Chatbot with RAG, pgvector, Document Workspace, and Empathetic Support.",
    version="1.0.0",
    lifespan=lifespan
)

# Register Security, Observability, and Rate Limiting Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdAndLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS Middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded media files statically
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include API Routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(conversations.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(uploads.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(audio.router, prefix=settings.API_V1_STR)
app.include_router(images.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(memory.router, prefix=settings.API_V1_STR)
app.include_router(feedback.router, prefix=settings.API_V1_STR)
app.include_router(jobs.router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "Welcome to Multimodal AI Chatbot API",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
