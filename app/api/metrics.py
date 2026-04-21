"""
System Metrics Router for Aviation RAG.
Exposes performance telemetry for observability and monitoring.
"""

from fastapi import APIRouter
from app.services.metrics import get_metrics

router = APIRouter()

@router.get("/metrics")
def metrics():
    """
    Exposes production metrics for system observability and monitoring.
    """
    return get_metrics()
