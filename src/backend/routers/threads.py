from fastapi import APIRouter, HTTPException
from typing import List
from ..models import ThreadCreate, ThreadResponse, MessageCreate, MessageResponse
from ..database import threads_db, messages_db
import uuid
import time

router = APIRouter()

# 스레드 생성 (Create a thread)
@router.post("/threads", response_model=ThreadResponse)
async def create_thread(thread: ThreadCreate):
    thread_id = str(uuid.uuid4())
    new_thread = ThreadResponse(
        id=thread_id,
        metadata=thread.metadata or {},
        created_at=int(time.time())
    )
    threads_db[thread_id] = new_thread
    messages_db[thread_id] = []
    return new_thread

# 스레드 조회 (Get a thread)
@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str):
    if thread_id not in threads_db:
        raise HTTPException(status_code=404, detail="스레드를 찾을 수 없습니다.")
    return threads_db[thread_id]

# 스레드 삭제 (Delete a thread)
@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    if thread_id not in threads_db:
        raise HTTPException(status_code=404, detail="스레드를 찾을 수 없습니다.")
    del threads_db[thread_id]
    del messages_db[thread_id]
    return {"message": "스레드가 성공적으로 삭제되었습니다."}

# 메시지 목록 조회 (List messages)
@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
async def list_messages(thread_id: str):
    if thread_id not in threads_db:
        raise HTTPException(status_code=404, detail="스레드를 찾을 수 없습니다.")
    return messages_db.get(thread_id, [])

# 메시지 추가 (Add a message)
@router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
async def create_message(thread_id: str, message: MessageCreate):
    if thread_id not in threads_db:
        raise HTTPException(status_code=404, detail="스레드를 찾을 수 없습니다.")
    
    msg_id = str(uuid.uuid4())
    new_message = MessageResponse(
        id=msg_id,
        thread_id=thread_id,
        role=message.role,
        content=[{"type": "text", "text": {"value": message.content}}], # 단순화된 메시지 구조
        attachments=message.attachments or [],
        created_at=int(time.time())
    )
    messages_db[thread_id].append(new_message)
    return new_message
