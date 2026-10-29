from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings
from app.core.metrics import metrics_collector

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/live", status_code=status.HTTP_200_OK)
def liveness_probe():
    """
    Kubernetes / Docker lightweight liveness probe.
    Returns 200 OK immediately if the ASGI process is running.
    """
    return {"status": "alive"}

@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness_probe(db: Session = Depends(get_db)):
    """
    Kubernetes / Docker readiness probe.
    Validates that database connectivity is healthy and ready to accept traffic.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: Database check failed ({e})"
        )

@router.get("/metrics")
def get_system_metrics():
    """
    Returns aggregated observability telemetry:
    uptime, total requests, error rate, average latency, and estimated AI token cost.
    """
    return metrics_collector.get_summary()

@router.get("")
def health_check(db: Session = Depends(get_db)):
    """
    Returns server health, database connectivity, and active AI providers.
    """
    db_status = "healthy"
    dialect = "unknown"
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy ({str(e)})"

    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "database": {
            "status": db_status,
            "dialect": dialect
        },
        "providers": {
            "llm": settings.LLM_PROVIDER,
            "llm_model": settings.OPENAI_MODEL if settings.LLM_PROVIDER == "openai" else settings.GEMINI_MODEL,
            "embedding": settings.EMBEDDING_PROVIDER,
            "embedding_dim": settings.EMBEDDING_DIM,
            "search": settings.SEARCH_PROVIDER
        }
    }
