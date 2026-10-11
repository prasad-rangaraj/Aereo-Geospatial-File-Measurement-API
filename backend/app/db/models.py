"""SQLAlchemy data models for files and spatial features."""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey
)
from sqlalchemy.orm import relationship
from app.db.database import Base

class FileRecord(Base):
    """Stores metadata for uploaded geospatial files."""
    __tablename__ = "file_records"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # 'shapefile' or 'kml'
    file_size_bytes = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="PENDING", index=True)  # PENDING, PROCESSING, COMPLETED, FAILED
    feature_count = Column(Integer, nullable=False, default=0)
    source_crs = Column(String(100), nullable=True)
    projected_crs = Column(String(100), nullable=True)
    bounds_json = Column(Text, nullable=True)  # [minx, miny, maxx, maxy]
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    features = relationship("FeatureRecord", back_populates="file_record", cascade="all, delete-orphan", order_by="FeatureRecord.feature_index")

    @property
    def bounds(self) -> Optional[List[float]]:
        if self.bounds_json:
            try:
                return json.loads(self.bounds_json)
            except Exception:
                return None
        return None

    @bounds.setter
    def bounds(self, value: Optional[List[float]]) -> None:
        if value is not None:
            self.bounds_json = json.dumps(value)
        else:
            self.bounds_json = None


class FeatureRecord(Base):
    """Stores spatial geometry, properties, and computed measurements for an individual feature."""
    __tablename__ = "feature_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(36), ForeignKey("file_records.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_index = Column(Integer, nullable=False)
    feature_identifier = Column(String(255), nullable=True)
    geometry_type = Column(String(50), nullable=False)  # Polygon, LineString, Point, MultiPolygon, etc.
    
    properties_json = Column(Text, nullable=False, default="{}")
    geometry_geojson = Column(Text, nullable=True)  # GeoJSON representation in source CRS
    
    # Measurements in projected CRS
    area_sq_m = Column(Float, nullable=True)
    area_hectares = Column(Float, nullable=True)
    perimeter_m = Column(Float, nullable=True)
    length_m = Column(Float, nullable=True)
    length_km = Column(Float, nullable=True)
    
    measurement_status = Column(String(50), nullable=False, default="CALCULATED")  # CALCULATED, NOT_APPLICABLE, UNSUPPORTED, INVALID_GEOMETRY
    notes = Column(Text, nullable=True)

    file_record = relationship("FileRecord", back_populates="features")

    @property
    def properties(self) -> Dict[str, Any]:
        if self.properties_json:
            try:
                return json.loads(self.properties_json)
            except Exception:
                return {}
        return {}

    @properties.setter
    def properties(self, value: Dict[str, Any]) -> None:
        self.properties_json = json.dumps(value or {})

    @property
    def geometry(self) -> Optional[Dict[str, Any]]:
        if self.geometry_geojson:
            try:
                return json.loads(self.geometry_geojson)
            except Exception:
                return None
        return None

    @geometry.setter
    def geometry(self, value: Optional[Dict[str, Any]]) -> None:
        if value is not None:
            self.geometry_geojson = json.dumps(value)
        else:
            self.geometry_geojson = None
