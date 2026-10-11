"""Pydantic schemas for request and response validation."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class FileUploadResponse(BaseModel):
    id: str = Field(..., description="Unique file UUID")
    filename: str = Field(..., description="Uploaded file name")
    file_type: str = Field(..., description="Identified file format: 'shapefile' or 'kml'")
    status: str = Field(..., description="Processing state: PENDING, PROCESSING, COMPLETED, FAILED")
    message: str = Field(..., description="Status summary message")

    model_config = {"from_attributes": True}


class FileInfoResponse(BaseModel):
    id: str = Field(..., description="Unique file UUID")
    filename: str = Field(..., description="Uploaded file name")
    file_type: str = Field(..., description="Format: 'shapefile' or 'kml'")
    file_size_bytes: int = Field(..., description="Size in bytes")
    feature_count: int = Field(..., description="Number of extracted geospatial features")
    crs: Optional[str] = Field(None, description="Source Coordinate Reference System (e.g. EPSG:4326)")
    projected_crs: Optional[str] = Field(None, description="Projected Coordinate Reference System used for metric calculations")
    status: str = Field(..., description="Processing state: PENDING, PROCESSING, COMPLETED, FAILED")
    bounds: Optional[List[float]] = Field(None, description="Bounding box [min_lon, min_lat, max_lon, max_lat]")
    error_message: Optional[str] = Field(None, description="Error details if processing failed")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")

    model_config = {"from_attributes": True}


class FeatureMeasurementDetail(BaseModel):
    area_sq_m: Optional[float] = Field(None, description="Planar area in square meters (m²)")
    area_hectares: Optional[float] = Field(None, description="Area in hectares (1 ha = 10,000 m²)")
    perimeter_m: Optional[float] = Field(None, description="Boundary perimeter in meters (m)")
    length_m: Optional[float] = Field(None, description="Planar length in meters (m)")
    length_km: Optional[float] = Field(None, description="Length in kilometers (km)")
    status: str = Field(..., description="Status: CALCULATED, NOT_APPLICABLE, UNSUPPORTED, INVALID_GEOMETRY")
    note: Optional[str] = Field(None, description="Additional context or reason for calculation status")


class FeatureResponse(BaseModel):
    feature_index: int = Field(..., description="0-indexed position of feature in file")
    feature_id: Optional[str] = Field(None, description="Feature identifier/name if present")
    geometry_type: str = Field(..., description="Geometry type (Polygon, LineString, Point, etc.)")
    geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON geometry dictionary in source coordinates")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Attributes/properties extracted from the feature")
    measurement: FeatureMeasurementDetail = Field(..., description="Calculated metric measurements")

    model_config = {"from_attributes": True}


class MeasurementSummary(BaseModel):
    total_features: int = Field(..., description="Total feature count in dataset")
    calculated_features: int = Field(..., description="Number of features with calculated measurements")
    polygon_count: int = Field(..., description="Number of Polygon / MultiPolygon features")
    linestring_count: int = Field(..., description="Number of LineString / MultiLineString features")
    point_count: int = Field(..., description="Number of Point / MultiPoint features")
    other_count: int = Field(..., description="Number of other / unsupported geometries")
    total_area_sq_m: float = Field(..., description="Sum of all polygon areas in square meters (m²)")
    total_area_hectares: float = Field(..., description="Sum of all polygon areas in hectares (ha)")
    total_length_m: float = Field(..., description="Sum of all linestring lengths in meters (m)")
    total_length_km: float = Field(..., description="Sum of all linestring lengths in kilometers (km)")
    projected_crs: Optional[str] = Field(None, description="Projected CRS applied for Euclidean calculations")


class FileMeasurementsResponse(BaseModel):
    id: str = Field(..., description="File ID")
    filename: str = Field(..., description="Source filename")
    status: str = Field(..., description="Processing status")
    source_crs: Optional[str] = Field(None, description="Source CRS")
    projected_crs: Optional[str] = Field(None, description="Target projected CRS")
    summary: MeasurementSummary = Field(..., description="Aggregated dataset metrics")
    features: List[FeatureResponse] = Field(default_factory=list, description="Per-feature measurements and attributes")

    model_config = {"from_attributes": True}
