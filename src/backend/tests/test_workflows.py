
from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_workflow_execution_flow():
    # 1. 워크플로우 목록 조회
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    workflows = response.json().get("workflows", [])
    assert len(workflows) > 0
    target_workflow = workflows[0]  # hr-onboarding

    # 2. 워크플로우 실행 (Plan)
    input_data = {"inputs": {"name": "Test User", "role": "Tester"}}
    response = client.post(f"/api/v1/workflows/{target_workflow}/execute", json=input_data)
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_name"] == target_workflow
    
    execution_id = data["execution_id"]
    
    if target_workflow == "hr-onboarding":
        assert data["status"] == "waiting_for_approval"
        
        # 3. 승인 (Approve)
        response = client.post(f"/api/v1/workflows/executions/{execution_id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
    else:
         assert data["status"] in ["queued", "running"]

    # 4. 실행 상태 조회 (Polling wait could be needed in real integration test, but here just check api works)
    response = client.get(f"/api/v1/workflows/executions/{execution_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["execution_id"] == execution_id
