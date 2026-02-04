from fastapi.testclient import TestClient
from src.backend.main import app
import uuid

client = TestClient(app)

def test_thread_and_messages_flow():
    # 0. 테스트용 에이전트 생성
    unique_name = f"Test-Agent-Korean-{uuid.uuid4().hex[:8]}"
    agent_data = {
        "name": unique_name,
        "model": "gpt-4o-mini",
        "instructions": "테스트용 에이전트입니다.",
        "tools": []
    }
    response = client.post("/api/v1/agents", json=agent_data)
    assert response.status_code == 200
    agent_id = response.json()["id"]

    thread_id = None
    try:
        # 1. 스레드 생성
        response = client.post("/api/v1/threads", json={"metadata": {}})
        if response.status_code != 200:
            print(f"Thread Create Failed: {response.json()}")
        assert response.status_code == 200
        thread_data = response.json()
        thread_id = thread_data["id"]

        # 2. 스레드 조회
        response = client.get(f"/api/v1/threads/{thread_id}")
        assert response.status_code == 200
        assert response.json()["id"] == thread_id

        # 3. 메시지 추가
        msg_data = {
            "role": "user",
            "content": "안녕하세요? 반가워요."
        }
        response = client.post(f"/api/v1/threads/{thread_id}/messages", json=msg_data)
        assert response.status_code == 200
        msg_data_res = response.json()
        assert msg_data_res["role"] == "user"
        # Content check: "안녕하세요? 반가워요." in the first text element
        # API returns list of content blocks
        assert msg_data_res["content"][0]["text"]["value"] == "안녕하세요? 반가워요."

        # 4. 메시지 목록 조회
        response = client.get(f"/api/v1/threads/{thread_id}/messages")
        assert response.status_code == 200
        assert len(response.json()) >= 1
        
        # 5. 실행 (Run) 생성
        run_data = {
            "agent_id": agent_id,
            "instructions": "짧게 대답해 주세요."
        }
        response = client.post(f"/api/v1/threads/{thread_id}/runs", json=run_data)
        if response.status_code != 200:
            print(f"Run Create Failed: {response.json()}")
        assert response.status_code == 200
        run_id = response.json()["id"]
        
        # 6. 실행 상태 조회
        response = client.get(f"/api/v1/threads/{thread_id}/runs/{run_id}")
        assert response.status_code == 200
        assert response.json()["status"] in ["queued", "in_progress", "completed", "requires_action"]

    finally:
        # Cleanup
        if thread_id:
             client.delete(f"/api/v1/threads/{thread_id}")
        client.delete(f"/api/v1/agents/{agent_id}")

