"""
Health Check Router for Aviation RAG.
Provides a standard endpoint for operational readiness and uptime monitoring.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    """
    Standard health check endpoint for container orchestrators (K8s/Docker).
    Verifies that the API service is reachable.
    """
    return {"status": "ok"}
