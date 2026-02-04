from fastapi.testclient import TestClient
from src.backend.main import app
import uuid

client = TestClient(app)

def test_create_and_list_agents():
    # 1. 에이전트 목록 조회 (초기에는 비어있거나 기존 에이전트가 있어야 함)
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    initial_count = len(response.json())

    # 2. 새 에이전트 생성
    unique_name = f"Test-Agent-{uuid.uuid4().hex[:8]}"
    agent_data = {
        "name": unique_name,
        "model": "gpt-4o-mini",
        "instructions": "You are a test agent.",
        "tools": ["code_interpreter"]
    }
    response = client.post("/api/v1/agents", json=agent_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == agent_data["name"]
    assert data["model"] == agent_data["model"]
    assert "id" in data
    agent_id = data["id"]

    try:
        # 3. 특정 에이전트 조회
        response = client.get(f"/api/v1/agents/{agent_id}")
        assert response.status_code == 200
        assert response.json()["id"] == agent_id

        # 4. 조회된 목록에 포함되어 있는지 확인
        response = client.get("/api/v1/agents")
        assert len(response.json()) >= initial_count + 1
        found = False
        for agent in response.json():
            if agent["id"] == agent_id:
                found = True
                break
        assert found
    finally:
        # Cleanup
        client.delete(f"/api/v1/agents/{agent_id}")

def test_delete_agent():
    # Setup: Create an agent to delete
    unique_name = f"Delete-Test-{uuid.uuid4().hex[:8]}"
    agent_data = {
        "name": unique_name,
        "model": "gpt-4o-mini",
        "instructions": "To be deleted."
    }
    response = client.post("/api/v1/agents", json=agent_data)
    assert response.status_code == 200
    agent_id = response.json()["id"]

    # Delete
    response = client.delete(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 200

    # Verify deletion
    response = client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 404

