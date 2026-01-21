from fastapi.testclient import TestClient
from src.backend.main import app
import sys
import os

# src 폴더를 sys.path에 추가하여 src 모듈을 임포트할 수 있도록 함
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

client = TestClient(app)

def test_create_and_list_agents():
    # 1. 에이전트 목록 조회 (초기에는 비어있거나 기존 에이전트가 있어야 함)
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    initial_count = len(response.json())

    # 2. 새 에이전트 생성
    agent_data = {
        "name": "Test Agent",
        "model": "gpt-4-test",
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

    # 3. 특정 에이전트 조회
    response = client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["id"] == agent_id

    # 4. 에이전트 목록 다시 조회 (1개 증가해야 함)
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert len(response.json()) == initial_count + 1

    # 5. 에이전트 수정
    update_data = {"name": "Updated Agent Name"}
    response = client.put(f"/api/v1/agents/{agent_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Agent Name"

    # 6. 에이전트 삭제
    response = client.delete(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 200

    # 7. Check if deleted
    response = client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 404
