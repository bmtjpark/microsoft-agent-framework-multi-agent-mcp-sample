from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_workflow_execution_flow():
    # 1. 워크플로우 목록 조회
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    workflows = response.json().get("workflows", [])
    assert len(workflows) > 0
    target_workflow = workflows[0]

    # 2. 워크플로우 실행
    input_data = {"inputs": {"topic": "Integration Testing"}}
    response = client.post(f"/api/v1/workflows/{target_workflow}/execute", json=input_data)
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_name"] == target_workflow
    assert data["status"] == "running"
    execution_id = data["execution_id"]

    # 3. 실행 상태 조회
    response = client.get(f"/api/v1/workflows/executions/{execution_id}")
    assert response.status_code == 200
    data = response.json()
    # 모의 로직은 조회 시 바로 완료 상태로 변경됨
    assert data["status"] == "completed" 
    assert data["result"] is not None
