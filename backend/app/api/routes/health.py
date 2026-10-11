"""Health check route."""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "supported_formats": [".kml", ".zip (Shapefile)"],
        "default_crs": settings.DEFAULT_FALLBACK_CRS
    }
