from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_thread_and_messages_flow():
    # 1. 스레드 생성
    response = client.post("/api/v1/threads", json={"metadata": {"test": "true"}})
    assert response.status_code == 200
    thread_data = response.json()
    thread_id = thread_data["id"]

    # 2. 스레드 조회
    response = client.get(f"/api/v1/threads/{thread_id}")
    assert response.status_code == 200
    assert response.json()["id"] == thread_id

    # 3. 메시지 추가
    message_data = {"role": "user", "content": "Hello Agent!"}
    response = client.post(f"/api/v1/threads/{thread_id}/messages", json=message_data)
    assert response.status_code == 200
    msg_data = response.json()
    assert msg_data["role"] == "user"
    assert msg_data["thread_id"] == thread_id

    # 4. 메시지 목록 조회
    response = client.get(f"/api/v1/threads/{thread_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 1
    assert messages[0]["id"] == msg_data["id"]

    # 5. 실행 시작 (모의)
    run_req = {"agent_id": "test-agent-id"}
    response = client.post(f"/api/v1/threads/{thread_id}/runs", json=run_req)
    assert response.status_code == 200
    run_data = response.json()
    run_id = run_data["id"]
    assert run_data["status"] == "queued"

    # 6. 실행 상태 조회
    response = client.get(f"/api/v1/threads/{thread_id}/runs/{run_id}")
    assert response.status_code == 200
    # 조회 시 모의 로직이 상태를 업데이트함
    assert response.json()["status"] in ["in_progress", "completed"]

    # 7. 스레드 삭제
    response = client.delete(f"/api/v1/threads/{thread_id}")
    assert response.status_code == 200
    
    # 삭제 확인
    response = client.get(f"/api/v1/threads/{thread_id}")
    assert response.status_code == 404
