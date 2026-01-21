from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Microsoft Agent Framework API"}

def test_list_agents_empty():
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
