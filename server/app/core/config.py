"""Application configuration settings."""
import os
from pathlib import Path
from pydantic import BaseModel, Field

class Settings(BaseModel):
    PROJECT_NAME: str = "Aereo Geospatial File Measurement API"
    PROJECT_DESCRIPTION: str = (
        "Enterprise-ready API for uploading geospatial files (Shapefile ZIP, KML), "
        "accurate metric measurement calculation with dynamic projected CRS transformation."
    )
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/geospatial.db")
    
    # GIS Projection Defaults
    DEFAULT_FALLBACK_CRS: str = "EPSG:4326"
    
    def init_directories(self) -> None:
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.init_directories()
