"""Geospatial coordinate reference system (CRS) resolution and geometry transformation engine."""
import math
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pyproj
import shapely
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

logger = logging.getLogger("aereo.geometry_processor")

def parse_crs(crs_input: Optional[str]) -> Optional[pyproj.CRS]:
    """
    Parse a CRS from an EPSG string, authority code, or ESRI WKT string.
    Returns pyproj.CRS instance, or None if unparseable/absent.
    """
    if not crs_input or not crs_input.strip():
        return None
    
    clean_input = crs_input.strip()
    try:
        return pyproj.CRS.from_user_input(clean_input)
    except Exception as e:
        logger.warning(f"Could not parse CRS directly from input '{clean_input[:50]}...': {e}")
        # Try fallback for ESRI WKT
        try:
            return pyproj.CRS.from_wkt(clean_input)
        except Exception:
            return None

def get_utm_epsg(lon: float, lat: float) -> int:
    """
    Calculate the EPSG code for the optimal local Universal Transverse Mercator (UTM) zone.
    Earth is split into 60 zones of 6 degrees longitude each:
      Zone = floor((lon + 180) / 6) + 1
      EPSG: 32601-32660 for Northern Hemisphere (lat >= 0)
      EPSG: 32701-32760 for Southern Hemisphere (lat < 0)
    """
    # Normalize longitude to [-180, 180)
    norm_lon = ((lon + 180.0) % 360.0) - 180.0
    zone = int(math.floor((norm_lon + 180.0) / 6.0)) + 1
    zone = max(1, min(60, zone))
    
    if lat >= 0:
        return 32600 + zone
    else:
        return 32700 + zone

def select_projected_crs(
    source_crs: Optional[pyproj.CRS],
    bounds: Optional[List[float]] = None,
    centroid_coords: Optional[Tuple[float, float]] = None
) -> Tuple[pyproj.CRS, str]:
    """
    Select an appropriate projected Coordinate Reference System for accurate metric calculations.
    
    Strategy:
    1. If source_crs is ALREADY a projected CRS with meter units (e.g., existing UTM, State Plane),
       retain it.
    2. If source_crs is geographic (degrees, e.g. EPSG:4326):
       - If centroid or bounds available, dynamically select the local UTM projection.
       - If bounds span more than 6 degrees longitude (multi-zone), select EPSG:6933 (World Equal Area)
         to ensure true area conservation without extreme distortion.
       - If no coordinates are known, default to EPSG:3857 or EPSG:6933.
    """
    # 1. Check if already projected
    if source_crs and source_crs.is_projected:
        axis_units = [axis.unit_name for axis in source_crs.axis_info]
        if any("metre" in u.lower() or "meter" in u.lower() for u in axis_units):
            crs_id = f"EPSG:{source_crs.to_epsg()}" if source_crs.to_epsg() else source_crs.name
            return source_crs, f"{crs_id} (Preserved Source Projected CRS)"
    
    # 2. Extract representative center (lon, lat)
    center_lon, center_lat = 0.0, 0.0
    span_lon = 0.0
    
    if bounds and len(bounds) == 4:
        min_lon, min_lat, max_lon, max_lat = bounds
        center_lon = (min_lon + max_lon) / 2.0
        center_lat = (min_lat + max_lat) / 2.0
        span_lon = abs(max_lon - min_lon)
    elif centroid_coords:
        center_lon, center_lat = centroid_coords

    # Check multi-zone span
    if span_lon > 6.0:
        # Continental or global dataset spanning multiple UTM zones: use World Equal Area
        equal_area_crs = pyproj.CRS("EPSG:6933")
        return equal_area_crs, "EPSG:6933 (World Equal Area - Selected for Multi-Zone Geographic Coverage)"
    
    # Local survey dataset: select optimal local UTM zone
    utm_code = get_utm_epsg(center_lon, center_lat)
    target_crs = pyproj.CRS(f"EPSG:{utm_code}")
    hemisphere = "N" if center_lat >= 0 else "S"
    zone = utm_code % 100
    description = f"EPSG:{utm_code} (WGS 84 / UTM Zone {zone}{hemisphere})"
    return target_crs, description

def create_reprojector(src_crs: pyproj.CRS, dst_crs: pyproj.CRS) -> Callable[[np.ndarray], np.ndarray]:
    """
    Create a coordinate reprojection callable for Shapely 2.0.
    Handles both 2D (x, y) and 3D (x, y, z) coordinate arrays gracefully.
    """
    transformer = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)

    def _transform_coords(coords: np.ndarray) -> np.ndarray:
        if coords.size == 0:
            return coords
        x, y = coords[:, 0], coords[:, 1]
        x_proj, y_proj = transformer.transform(x, y)
        if coords.shape[1] > 2:
            # Preserve elevation Z intact
            return np.column_stack([x_proj, y_proj, coords[:, 2]])
        return np.column_stack([x_proj, y_proj])

    return _transform_coords

def reproject_geometry(
    geometry: BaseGeometry,
    reprojector: Callable[[np.ndarray], np.ndarray]
) -> BaseGeometry:
    """Reproject a Shapely geometry using an array-based coordinate transformer."""
    return shapely.transform(geometry, reprojector)

def sanitize_geometry(geom: BaseGeometry) -> Tuple[BaseGeometry, bool, Optional[str]]:
    """
    Check geometry validity. If invalid, attempt non-destructive repair using make_valid.
    Returns (cleaned_geometry, was_repaired, note).
    """
    if geom.is_valid:
        return geom, False, None
    
    try:
        repaired = make_valid(geom)
        return repaired, True, "Geometry was self-intersecting or topologically invalid; repaired via make_valid()."
    except Exception as e:
        return geom, False, f"Geometry is invalid and could not be automatically repaired: {str(e)}"
