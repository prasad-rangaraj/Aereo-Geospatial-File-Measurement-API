"""Pytest test configuration and fixtures."""
import io
import os
import zipfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import shapefile

from app.main import app
from app.db.database import Base, get_db
from app.core.config import settings

from sqlalchemy.pool import StaticPool

# In-memory SQLite database for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_kml_bytes() -> bytes:
    sample_file = Path(__file__).resolve().parent.parent / "sample_data" / "survey_bengaluru.kml"
    return sample_file.read_bytes()

@pytest.fixture
def sample_shapefile_zip_bytes() -> bytes:
    sample_file = Path(__file__).resolve().parent.parent / "sample_data" / "cadastral_parcels.zip"
    return sample_file.read_bytes()
