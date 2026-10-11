"""Tests for spatial measurements (Polygon area, LineString length, Point no-measurement)."""
import pytest
from fastapi.testclient import TestClient

def test_polygon_area_and_linestring_length_kml(client: TestClient, sample_kml_bytes: bytes):
    upload_res = client.post(
        "/api/files/",
        files={"file": ("survey_bengaluru.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    file_id = upload_res.json()["id"]

    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    data = meas_res.json()

    summary = data["summary"]
    assert summary["total_features"] == 4
    assert summary["polygon_count"] == 2
    assert summary["linestring_count"] == 1
    assert summary["point_count"] == 1
    assert summary["total_area_sq_m"] > 0
    assert summary["total_area_hectares"] > 0
    assert summary["total_length_m"] > 0

    features = data["features"]

    # Feature 0: Zone A Construction Site (Polygon)
    f0 = features[0]
    assert f0["geometry_type"] == "Polygon"
    assert f0["measurement"]["status"] == "CALCULATED"
    assert f0["measurement"]["area_sq_m"] > 100000.0  # Approx 400m x 440m ~ 170,000 m²
    assert f0["measurement"]["area_hectares"] > 10.0
    assert f0["measurement"]["perimeter_m"] > 1000.0
    assert f0["measurement"]["length_m"] is None

    # Feature 1: Zone B Solar Array with hole (Polygon)
    f1 = features[1]
    assert f1["geometry_type"] == "Polygon"
    assert f1["measurement"]["status"] == "CALCULATED"
    assert f1["measurement"]["area_sq_m"] > 0
    assert f1["measurement"]["area_hectares"] > 0

    # Feature 2: Primary Haul Road (LineString)
    f2 = features[2]
    assert f2["geometry_type"] == "LineString"
    assert f2["measurement"]["status"] == "CALCULATED"
    assert f2["measurement"]["length_m"] > 500.0
    assert f2["measurement"]["length_km"] > 0.5
    assert f2["measurement"]["area_sq_m"] is None

    # Feature 3: RTK GNSS Base Station (Point)
    f3 = features[3]
    assert f3["geometry_type"] == "Point"
    assert f3["measurement"]["status"] == "NOT_APPLICABLE"
    assert f3["measurement"]["area_sq_m"] is None
    assert f3["measurement"]["length_m"] is None
    assert "Point geometry" in f3["measurement"]["note"]

def test_shapefile_measurements(client: TestClient, sample_shapefile_zip_bytes: bytes):
    upload_res = client.post(
        "/api/files/",
        files={"file": ("cadastral_parcels.zip", sample_shapefile_zip_bytes, "application/zip")}
    )
    file_id = upload_res.json()["id"]

    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    data = meas_res.json()

    assert data["summary"]["polygon_count"] == 3
    assert data["summary"]["total_area_sq_m"] > 400000.0
    assert data["summary"]["total_area_hectares"] > 40.0

    for feat in data["features"]:
        assert feat["geometry_type"] == "Polygon"
        assert feat["measurement"]["status"] == "CALCULATED"
        assert feat["measurement"]["area_sq_m"] > 0
        assert feat["measurement"]["perimeter_m"] > 0
        assert "parcel_id" in feat["properties"]

def test_geojson_export_endpoint(client: TestClient, sample_kml_bytes: bytes):
    upload_res = client.post(
        "/api/files/",
        files={"file": ("survey_bengaluru.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    file_id = upload_res.json()["id"]

    geo_res = client.get(f"/api/files/{file_id}/geojson/")
    assert geo_res.status_code == 200
    geojson = geo_res.json()

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 4
    first_feat = geojson["features"][0]
    assert "_measurement" in first_feat["properties"]
    assert first_feat["properties"]["_measurement"]["status"] == "CALCULATED"
