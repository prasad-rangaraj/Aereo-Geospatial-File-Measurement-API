"""Tests for error handling, corrupted files, and graceful edge-case resilience."""
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
import shapefile

def test_corrupted_zip_upload(client: TestClient):
    corrupt_data = b"PK\x03\x04CORRUPTED_NON_ZIP_BYTES"
    response = client.post(
        "/api/files/",
        files={"file": ("corrupt.zip", corrupt_data, "application/zip")}
    )
    assert response.status_code == 422
    assert "not a valid zip" in response.json()["detail"].lower()

def test_shapefile_missing_shp_file(client: TestClient):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("test.txt", "Some random text")
    
    response = client.post(
        "/api/files/",
        files={"file": ("missing_shp.zip", zip_buf.getvalue(), "application/zip")}
    )
    assert response.status_code == 422
    assert "missing required .shp" in response.json()["detail"].lower()

def test_shapefile_missing_shx_companion(client: TestClient):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("layer.shp", b"dummy")
        zf.writestr("layer.dbf", b"dummy")
        # Missing layer.shx!

    response = client.post(
        "/api/files/",
        files={"file": ("missing_shx.zip", zip_buf.getvalue(), "application/zip")}
    )
    assert response.status_code == 422
    assert "missing" in response.json()["detail"].lower()

def test_shapefile_missing_prj_handled_gracefully(client: TestClient):
    """Shapefile without .prj should NOT crash; it defaults to fallback EPSG:4326."""
    shp_buf = io.BytesIO()
    shx_buf = io.BytesIO()
    dbf_buf = io.BytesIO()

    w = shapefile.Writer(shp=shp_buf, shx=shx_buf, dbf=dbf_buf, shapeType=shapefile.POLYGON)
    w.field('name', 'C')
    w.poly([[[77.59, 12.97], [77.60, 12.97], [77.60, 12.98], [77.59, 12.98], [77.59, 12.97]]])
    w.record('No PRJ Parcel')
    w.close()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("noprj.shp", shp_buf.getvalue())
        zf.writestr("noprj.shx", shx_buf.getvalue())
        zf.writestr("noprj.dbf", dbf_buf.getvalue())
        # Intentionally no .prj file!

    response = client.post(
        "/api/files/",
        files={"file": ("noprj.zip", zip_buf.getvalue(), "application/zip")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert "EPSG:4326" in data["crs"]  # Default fallback applied

def test_corrupted_kml_xml(client: TestClient):
    corrupt_xml = b"<kml><unclosed_tag>broken</kml>"
    response = client.post(
        "/api/files/",
        files={"file": ("broken.kml", corrupt_xml, "application/vnd.google-earth.kml+xml")}
    )
    assert response.status_code == 422
    assert "malformed or invalid kml" in response.json()["detail"].lower()

def test_kml_with_invalid_self_intersecting_polygon(client: TestClient):
    """Self-intersecting bowtie polygon is sanitized via make_valid without crashing the API."""
    bowtie_kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document>
        <Placemark>
          <name>Bowtie Self Intersecting</name>
          <Polygon>
            <outerBoundaryIs>
              <LinearRing>
                <coordinates>
                  77.59,12.97,0
                  77.60,12.98,0
                  77.59,12.98,0
                  77.60,12.97,0
                  77.59,12.97,0
                </coordinates>
              </LinearRing>
            </outerBoundaryIs>
          </Polygon>
        </Placemark>
      </Document>
    </kml>
    """.encode('utf-8')

    response = client.post(
        "/api/files/",
        files={"file": ("bowtie.kml", bowtie_kml, "application/vnd.google-earth.kml+xml")}
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    feat = meas_res.json()["features"][0]
    assert feat["measurement"]["status"] == "CALCULATED"
    assert feat["measurement"]["area_sq_m"] > 0
