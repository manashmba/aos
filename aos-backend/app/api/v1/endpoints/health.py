"""
AOS Health Check Endpoints
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "aos-backend",
        "version": "0.1.0",
    }
