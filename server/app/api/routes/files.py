"""Geospatial file upload, inspection, and measurement API endpoints."""
import uuid
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import FileRecord, FeatureRecord
from app.schemas.file import (
    FileInfoResponse,
    FeatureMeasurementDetail,
    FeatureResponse,
    MeasurementSummary,
    FileMeasurementsResponse,
)
from app.services.measurement_service import process_geospatial_file

logger = logging.getLogger("aereo.api.files")

router = APIRouter(prefix="/files", tags=["Geospatial Files"])

@router.post(
    "/",
    response_model=FileInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a geospatial file",
    description="Accepts a .kml file or a .zip archive containing an ESRI Shapefile (.shp, .shx, .dbf, .prj)."
)
async def upload_geospatial_file(
    file: UploadFile = File(..., description="Geospatial file (.kml or .zip Shapefile)"),
    db: Session = Depends(get_db)
):
    """
    Upload and process geospatial data:
    1. Validates extension (.kml or .zip).
    2. Enforces maximum upload payload limit.
    3. Extracts vector features and coordinate reference system.
    4. Dynamically projects to optimal local metric CRS and computes measurements.
    5. Persists metadata and measurements.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must not be empty."
        )

    filename = file.filename
    lower_name = filename.lower()
    
    if lower_name.endswith(".zip"):
        file_type = "shapefile"
    elif lower_name.endswith(".kml"):
        file_type = "kml"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{filename}'. Please upload a .kml file or a .zip containing a Shapefile."
        )

    # Read uploaded bytes with size safeguard
    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
        )

    # Create initial FileRecord
    file_id = str(uuid.uuid4())
    record = FileRecord(
        id=file_id,
        filename=filename,
        file_type=file_type,
        file_size_bytes=file_size,
        status="PENDING",
        feature_count=0
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Process file and calculate measurements
    processed_record = process_geospatial_file(
        file_id=file_id,
        filename=filename,
        file_bytes=contents,
        db=db
    )

    if processed_record.status == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File processing failed: {processed_record.error_message}"
        )

    return FileInfoResponse(
        id=processed_record.id,
        filename=processed_record.filename,
        file_type=processed_record.file_type,
        file_size_bytes=processed_record.file_size_bytes,
        feature_count=processed_record.feature_count,
        crs=processed_record.source_crs,
        projected_crs=processed_record.projected_crs,
        status=processed_record.status,
        bounds=processed_record.bounds,
        error_message=processed_record.error_message,
        created_at=processed_record.created_at,
        updated_at=processed_record.updated_at
    )


@router.get(
    "/{id}/",
    response_model=FileInfoResponse,
    summary="Get file information",
    description="Retrieve stored metadata, source CRS, projected CRS, and status for an uploaded file."
)
def get_file_info(
    id: str,
    db: Session = Depends(get_db)
):
    record = db.query(FileRecord).filter(FileRecord.id == id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{id}' was not found."
        )

    return FileInfoResponse(
        id=record.id,
        filename=record.filename,
        file_type=record.file_type,
        file_size_bytes=record.file_size_bytes,
        feature_count=record.feature_count,
        crs=record.source_crs,
        projected_crs=record.projected_crs,
        status=record.status,
        bounds=record.bounds,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at
    )


@router.get(
    "/{id}/measurements/",
    response_model=FileMeasurementsResponse,
    summary="Get file measurements",
    description="Returns computed metric measurements (area in m² & hectares, perimeter, length in m & km) for all features."
)
def get_file_measurements(
    id: str,
    db: Session = Depends(get_db)
):
    record = db.query(FileRecord).filter(FileRecord.id == id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{id}' was not found."
        )

    features: List[FeatureRecord] = record.features

    total_features = len(features)
    calculated_features = 0
    polygon_count = 0
    linestring_count = 0
    point_count = 0
    other_count = 0
    total_area_sq_m = 0.0
    total_length_m = 0.0

    feature_responses: List[FeatureResponse] = []

    for f in features:
        if f.measurement_status == "CALCULATED":
            calculated_features += 1

        if f.geometry_type in ("Polygon", "MultiPolygon"):
            polygon_count += 1
            if f.area_sq_m is not None:
                total_area_sq_m += f.area_sq_m
        elif f.geometry_type in ("LineString", "MultiLineString"):
            linestring_count += 1
            if f.length_m is not None:
                total_length_m += f.length_m
        elif f.geometry_type in ("Point", "MultiPoint"):
            point_count += 1
        else:
            other_count += 1

        meas_detail = FeatureMeasurementDetail(
            area_sq_m=f.area_sq_m,
            area_hectares=f.area_hectares,
            perimeter_m=f.perimeter_m,
            length_m=f.length_m,
            length_km=f.length_km,
            status=f.measurement_status,
            note=f.notes
        )

        feature_responses.append(
            FeatureResponse(
                feature_index=f.feature_index,
                feature_id=f.feature_identifier,
                geometry_type=f.geometry_type,
                geometry=f.geometry,
                properties=f.properties,
                measurement=meas_detail
            )
        )

    summary = MeasurementSummary(
        total_features=total_features,
        calculated_features=calculated_features,
        polygon_count=polygon_count,
        linestring_count=linestring_count,
        point_count=point_count,
        other_count=other_count,
        total_area_sq_m=round(total_area_sq_m, 2),
        total_area_hectares=round(total_area_sq_m / 10000.0, 4),
        total_length_m=round(total_length_m, 2),
        total_length_km=round(total_length_m / 1000.0, 4),
        projected_crs=record.projected_crs
    )

    return FileMeasurementsResponse(
        id=record.id,
        filename=record.filename,
        status=record.status,
        source_crs=record.source_crs,
        projected_crs=record.projected_crs,
        summary=summary,
        features=feature_responses
    )


@router.get(
    "/{id}/geojson/",
    summary="Export features as GeoJSON with measurements",
    description="Returns standard GeoJSON FeatureCollection embedded with calculated measurements in properties."
)
def export_file_geojson(
    id: str,
    db: Session = Depends(get_db)
):
    record = db.query(FileRecord).filter(FileRecord.id == id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{id}' was not found."
        )

    geojson_features = []
    for f in record.features:
        props = dict(f.properties)
        props["_measurement"] = {
            "geometry_type": f.geometry_type,
            "status": f.measurement_status,
            "area_sq_m": f.area_sq_m,
            "area_hectares": f.area_hectares,
            "perimeter_m": f.perimeter_m,
            "length_m": f.length_m,
            "length_km": f.length_km,
            "note": f.notes
        }
        geojson_features.append({
            "type": "Feature",
            "id": f.feature_identifier or f"feature_{f.feature_index}",
            "geometry": f.geometry,
            "properties": props
        })

    return {
        "type": "FeatureCollection",
        "metadata": {
            "id": record.id,
            "filename": record.filename,
            "source_crs": record.source_crs,
            "projected_crs": record.projected_crs,
            "feature_count": record.feature_count,
            "bounds": record.bounds
        },
        "features": geojson_features
    }


@router.delete(
    "/{id}/",
    status_code=status.HTTP_200_OK,
    summary="Delete a file and its measurements"
)
def delete_file(
    id: str,
    db: Session = Depends(get_db)
):
    record = db.query(FileRecord).filter(FileRecord.id == id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{id}' was not found."
        )
    db.delete(record)
    db.commit()
    return {"message": f"File '{id}' and associated measurements deleted successfully."}
