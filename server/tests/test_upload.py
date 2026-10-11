"""Tests for file upload, validation, and metadata retrieval."""
import io
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings

def test_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert ".kml" in data["supported_formats"]

def test_upload_valid_kml(client: TestClient, sample_kml_bytes: bytes):
    response = client.post(
        "/api/files/",
        files={"file": ("survey_bengaluru.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "survey_bengaluru.kml"
    assert data["file_type"] == "kml"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] == 4
    assert "EPSG:4326" in data["crs"]
    assert "UTM" in data["projected_crs"]

def test_upload_valid_shapefile_zip(client: TestClient, sample_shapefile_zip_bytes: bytes):
    response = client.post(
        "/api/files/",
        files={"file": ("cadastral_parcels.zip", sample_shapefile_zip_bytes, "application/zip")}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "cadastral_parcels.zip"
    assert data["file_type"] == "shapefile"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] == 3
    assert "UTM" in data["projected_crs"]

def test_get_file_info_persisted(client: TestClient, sample_kml_bytes: bytes):
    # Upload file
    upload_res = client.post(
        "/api/files/",
        files={"file": ("survey_bengaluru.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    file_id = upload_res.json()["id"]

    # Retrieve info in subsequent request
    get_res = client.get(f"/api/files/{file_id}/")
    assert get_res.status_code == 200
    info = get_res.json()
    assert info["id"] == file_id
    assert info["feature_count"] == 4
    assert info["status"] == "COMPLETED"

def test_get_nonexistent_file_404(client: TestClient):
    response = client.get("/api/files/non-existent-uuid-12345/")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_upload_unsupported_file_extension(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("document.pdf", b"%PDF-1.4 sample content", "application/pdf")}
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()

def test_upload_empty_file_rejected(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("empty.kml", b"", "application/vnd.google-earth.kml+xml")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_delete_file_endpoint(client: TestClient, sample_kml_bytes: bytes):
    upload_res = client.post(
        "/api/files/",
        files={"file": ("survey_bengaluru.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    file_id = upload_res.json()["id"]

    delete_res = client.delete(f"/api/files/{file_id}/")
    assert delete_res.status_code == 200

    # Ensure 404 after deletion
    get_res = client.get(f"/api/files/{file_id}/")
    assert get_res.status_code == 404
