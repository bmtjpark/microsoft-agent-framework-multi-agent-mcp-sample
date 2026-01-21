from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_system_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Microsoft Agent Framework API"}

def test_system_metrics():
    response = client.get("/api/v1/telemetry/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "active_runs" in data
    assert "completed_runs_today" in data
