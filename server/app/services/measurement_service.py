"""Geospatial measurement computation engine."""
import logging
from typing import Dict, List, Optional, Tuple
import pyproj
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import FileRecord, FeatureRecord
from app.services.file_reader import (
    read_kml_content,
    read_shapefile_zip,
    ExtractedDataset,
    ExtractedFeature,
    GeospatialReaderError,
)
from app.services.geometry_processor import (
    parse_crs,
    select_projected_crs,
    create_reprojector,
    reproject_geometry,
    sanitize_geometry,
)

logger = logging.getLogger("aereo.measurement_service")

class ProcessingResult:
    def __init__(self, file_record: FileRecord, dataset: Optional[ExtractedDataset] = None):
        self.file_record = file_record
        self.dataset = dataset


def process_geospatial_file(
    file_id: str,
    filename: str,
    file_bytes: bytes,
    db: Session
) -> FileRecord:
    """
    Main processing workflow:
    1. Retrieve file record and mark as PROCESSING.
    2. Parse features based on file extension (.kml or .zip shapefile).
    3. Identify source CRS and determine optimal local projected CRS.
    4. Reproject geometries and compute area (m², ha), perimeter (m), or length (m, km).
    5. Handle Point geometries and unsupported types gracefully without crashing.
    6. Persist results in the database with status COMPLETED or FAILED.
    """
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not record:
        raise ValueError(f"File record with ID '{file_id}' not found.")

    record.status = "PROCESSING"
    db.commit()

    lower_filename = filename.lower()
    try:
        # Step 1: Read spatial features
        if lower_filename.endswith(".kml"):
            dataset = read_kml_content(file_bytes, filename)
        elif lower_filename.endswith(".zip"):
            dataset = read_shapefile_zip(file_bytes, filename)
        else:
            raise GeospatialReaderError(
                f"Unsupported file format '{filename}'. Only .kml and .zip (Shapefile) are accepted."
            )

        # Step 2: Resolve Coordinate Reference System
        source_crs_str = dataset.source_crs_raw
        source_crs_obj = parse_crs(source_crs_str)

        if not source_crs_obj:
            logger.info("Source CRS not detected or specified; applying default EPSG:4326.")
            source_crs_obj = pyproj.CRS(settings.DEFAULT_FALLBACK_CRS)
            source_crs_display = f"{settings.DEFAULT_FALLBACK_CRS} (Default Fallback)"
        else:
            epsg_code = source_crs_obj.to_epsg()
            source_crs_display = f"EPSG:{epsg_code}" if epsg_code else source_crs_obj.name

        # Step 3: Determine target projected CRS (e.g. Local UTM Zone or World Equal Area)
        target_projected_crs, projected_crs_desc = select_projected_crs(
            source_crs=source_crs_obj,
            bounds=dataset.bounds
        )

        # Step 4: Construct coordinate reprojector
        reprojector = create_reprojector(source_crs_obj, target_projected_crs)

        # Step 5: Process individual features and calculate measurements
        feature_records: List[FeatureRecord] = []

        for feat in dataset.features:
            geom_type = feat.geometry_type
            raw_geom = feat.geometry

            # Clean/validate geometry
            clean_geom, was_repaired, repair_note = sanitize_geometry(raw_geom)
            
            feat_rec = FeatureRecord(
                file_id=record.id,
                feature_index=feat.index,
                feature_identifier=feat.identifier,
                geometry_type=geom_type,
                properties=feat.properties,
                geometry=feat.geojson_geometry,
                notes=repair_note
            )

            try:
                # Reproject geometry into projected CRS
                projected_geom = reproject_geometry(clean_geom, reprojector)

                if geom_type in ("Polygon", "MultiPolygon"):
                    area_sq_m = float(projected_geom.area)
                    perimeter_m = float(projected_geom.length)
                    feat_rec.area_sq_m = round(area_sq_m, 2)
                    feat_rec.area_hectares = round(area_sq_m / 10000.0, 4)
                    feat_rec.perimeter_m = round(perimeter_m, 2)
                    feat_rec.measurement_status = "CALCULATED"

                elif geom_type in ("LineString", "MultiLineString"):
                    length_m = float(projected_geom.length)
                    feat_rec.length_m = round(length_m, 2)
                    feat_rec.length_km = round(length_m / 1000.0, 4)
                    feat_rec.measurement_status = "CALCULATED"

                elif geom_type in ("Point", "MultiPoint"):
                    feat_rec.measurement_status = "NOT_APPLICABLE"
                    feat_rec.notes = "Point geometry: zero planar area and length applicable."

                elif geom_type == "GeometryCollection":
                    # Sum constituent polygon areas and line lengths
                    total_area = sum(float(g.area) for g in projected_geom.geoms if g.geom_type in ("Polygon", "MultiPolygon"))
                    total_length = sum(float(g.length) for g in projected_geom.geoms if g.geom_type in ("LineString", "MultiLineString"))
                    if total_area > 0:
                        feat_rec.area_sq_m = round(total_area, 2)
                        feat_rec.area_hectares = round(total_area / 10000.0, 4)
                    if total_length > 0:
                        feat_rec.length_m = round(total_length, 2)
                        feat_rec.length_km = round(total_length / 1000.0, 4)
                    feat_rec.measurement_status = "CALCULATED"
                    feat_rec.notes = "GeometryCollection: computed aggregate of constituent geometries."

                else:
                    feat_rec.measurement_status = "UNSUPPORTED"
                    feat_rec.notes = f"Unsupported geometry type '{geom_type}' for measurement calculations."

            except Exception as feat_err:
                logger.warning(f"Error calculating measurement for feature #{feat.index}: {feat_err}")
                feat_rec.measurement_status = "CALCULATION_ERROR"
                feat_rec.notes = f"Error during reprojection/measurement: {str(feat_err)}"

            feature_records.append(feat_rec)

        # Step 6: Update file metadata and save all feature records
        record.feature_count = len(feature_records)
        record.source_crs = source_crs_display
        record.projected_crs = projected_crs_desc
        record.bounds = dataset.bounds
        record.status = "COMPLETED"
        record.error_message = "; ".join(dataset.warnings) if dataset.warnings else None

        db.add_all(feature_records)
        db.commit()
        db.refresh(record)
        return record

    except Exception as e:
        logger.error(f"Failed to process file '{filename}': {e}", exc_info=True)
        record.status = "FAILED"
        record.error_message = str(e)
        db.commit()
        db.refresh(record)
        return record
