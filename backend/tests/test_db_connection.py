import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import check_falkordb_health

client = TestClient(app)


def test_system_health():
    """Verify that the FastAPI application is alive and responding."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_falkordb_direct_connection():
    """Verify direct Python SDK connectivity to FalkorDB on port 6379."""
    health = check_falkordb_health()
    assert health["status"] == "connected", f"FalkorDB connection failed: {health.get('error_message')}"
    assert health["query_verified"] is True
    assert health["host"] == "localhost"
    assert health["port"] == 6379


def test_api_db_health_endpoint():
    """Verify the /api/db-health endpoint returns 200 and connected status."""
    response = client.get("/api/db-health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["database"] == "FalkorDB"
    assert data["query_verified"] is True
