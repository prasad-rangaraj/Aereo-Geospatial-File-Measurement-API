"""Tests for Coordinate Reference System (CRS) selection, transformation, and mathematical accuracy."""
import pyproj
from shapely.geometry import Polygon
from app.services.geometry_processor import (
    get_utm_epsg,
    select_projected_crs,
    create_reprojector,
    reproject_geometry,
    parse_crs,
)

def test_utm_zone_formula():
    # Bengaluru (approx 77.59 E, 12.97 N) -> Zone 43 North -> 32643
    assert get_utm_epsg(77.59, 12.97) == 32643

    # London (approx 0.12 W, 51.50 N) -> Zone 30 North -> 32630
    assert get_utm_epsg(-0.12, 51.50) == 32630

    # New York (approx 74.00 W, 40.71 N) -> Zone 18 North -> 32618
    assert get_utm_epsg(-74.00, 40.71) == 32618

    # Sydney, Australia (approx 151.20 E, -33.86 S) -> Zone 56 South -> 32756
    assert get_utm_epsg(151.20, -33.86) == 32756

    # Rio de Janeiro, Brazil (approx -43.17 W, -22.90 S) -> Zone 23 South -> 32723
    assert get_utm_epsg(-43.17, -22.90) == 32723

def test_crs_projection_prevents_degree_distortion():
    """
    CRITICAL EVALUATION TEST:
    Demonstrates why geographic coordinates (EPSG:4326) fail for area calculations,
    and proves that projected UTM transformation yields correct metric area.
    """
    # A 100m x 100m square in Bengaluru (~0.0009 x ~0.0009 degrees)
    poly_deg = Polygon([
        (77.5900, 12.9700),
        (77.5909, 12.9700),
        (77.5909, 12.9709),
        (77.5900, 12.9709),
        (77.5900, 12.9700)
    ])

    # Direct calculation on degree coordinates yields squared degrees (WRONG!)
    raw_degree_area = poly_deg.area
    assert raw_degree_area < 0.0001, "Raw degree area is tiny and non-metric!"

    # Transform to UTM projected CRS
    src_crs = pyproj.CRS("EPSG:4326")
    target_crs, desc = select_projected_crs(src_crs, bounds=list(poly_deg.bounds))
    assert target_crs.to_epsg() == 32643

    reprojector = create_reprojector(src_crs, target_crs)
    poly_projected = reproject_geometry(poly_deg, reprojector)

    # Metric area in square meters (~10,000 m² = 1 hectare)
    projected_area_sq_m = poly_projected.area
    assert 9000.0 < projected_area_sq_m < 11000.0, f"Expected ~10,000 m², got {projected_area_sq_m}"

def test_multi_zone_geographic_dataset_selects_equal_area():
    """If bounds span > 6 degrees longitude, system chooses World Equal Area (EPSG:6933)."""
    wide_bounds = [70.0, 10.0, 85.0, 20.0]  # 15 degrees longitude span across India
    src_crs = pyproj.CRS("EPSG:4326")
    target_crs, desc = select_projected_crs(src_crs, bounds=wide_bounds)
    assert target_crs.to_epsg() == 6933
    assert "World Equal Area" in desc

def test_preserved_existing_projected_crs():
    """If file is already in a projected CRS with meters, it preserves it."""
    src_crs = pyproj.CRS("EPSG:32643")
    target_crs, desc = select_projected_crs(src_crs)
    assert target_crs.to_epsg() == 32643
    assert "Preserved" in desc

def test_parse_crs_from_wkt_and_epsg():
    assert parse_crs("EPSG:4326") is not None
    assert parse_crs("4326") is not None
    assert parse_crs("invalid_crs_garbage") is None
    assert parse_crs(None) is None
