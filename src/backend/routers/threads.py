from fastapi import APIRouter, HTTPException
from typing import List, Optional
from ..models import ThreadCreate, ThreadResponse, MessageCreate, MessageResponse
from ..client import get_inference_client
import time

router = APIRouter()

# 스레드 생성 (Create a thread)
@router.post("/threads", response_model=ThreadResponse)
async def create_thread(thread: ThreadCreate):
    client = get_inference_client()
    try:
        az_thread = client.beta.threads.create(metadata=thread.metadata)
        return ThreadResponse(
            id=az_thread.id,
            metadata=az_thread.metadata or {},
            created_at=az_thread.created_at
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"스레드 생성 실패: {str(e)}")

# 스레드 조회 (Get a thread)
@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str):
    client = get_inference_client()
    try:
        az_thread = client.beta.threads.retrieve(thread_id)
        return ThreadResponse(
            id=az_thread.id,
            metadata=az_thread.metadata or {},
            created_at=az_thread.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"스레드를 찾을 수 없습니다: {str(e)}")

# 스레드 삭제 (Delete a thread)
@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    client = get_inference_client()
    try:
        client.beta.threads.delete(thread_id)
        return {"message": "스레드가 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"스레드 삭제 실패: {str(e)}")

# 메시지 목록 조회 (List messages)
@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
async def list_messages(thread_id: str):
    client = get_inference_client()
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        
        response_messages = []
        for msg in messages.data:
            content_list = []
            for c in msg.content:
                if c.type == "text":
                    content_list.append({"type": "text", "text": {"value": c.text.value}})
                elif c.type == "image_file":
                    content_list.append({"type": "image_file", "image_file": {"file_id": c.image_file.file_id}})
            
            response_messages.append(MessageResponse(
                id=msg.id,
                thread_id=msg.thread_id,
                role=msg.role,
                content=content_list,
                attachments=[], 
                created_at=msg.created_at
            ))
        return response_messages
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"메시지 목록 조회 실패: {str(e)}")

# 메시지 추가 (Add a message)
@router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
async def create_message(thread_id: str, message: MessageCreate):
    client = get_inference_client()
    try:
        content_arg = ""
        # Handle message content safely
        if hasattr(message.content, "__iter__") and not isinstance(message.content, str):
             # It is a list (likely)
             if len(message.content) > 0 and hasattr(message.content[0], "text"):
                 content_arg = message.content[0].text.value
             else:
                 content_arg = " " 
        elif isinstance(message.content, str):
            content_arg = message.content
            
        created_msg = client.beta.threads.messages.create(
            thread_id=thread_id,
            role=message.role,
            content=content_arg
        )
        
        content_list = []
        for c in created_msg.content:
             if c.type == "text":
                content_list.append({"type": "text", "text": {"value": c.text.value}})
        
        return MessageResponse(
            id=created_msg.id,
            thread_id=created_msg.thread_id,
            role=created_msg.role,
            content=content_list,
            created_at=created_msg.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메시지 전송 실패: {str(e)}")

