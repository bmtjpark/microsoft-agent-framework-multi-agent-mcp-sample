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
    
    import os
    import pdfplumber
    from fastapi import status
    msg_id = str(uuid.uuid4())
    attachments = message.attachments or []
    if attachments and isinstance(attachments[0], str):
        attachments = [{"id": fid, "type": "unknown"} for fid in attachments]

    # 첨부파일이 PDF인 경우, 내용을 추출하여 content에 추가
    pdf_texts = []
    UPLOAD_DIR = "uploads"
    for att in attachments:
        if att.get("type", "").lower() == "pdf" or att.get("type", "").lower() == "application/pdf":
            file_id = att["id"]
            # 업로드 파일명 패턴: {file_id}_원본파일명
            for fname in os.listdir(UPLOAD_DIR):
                if fname.startswith(file_id + "_") and fname.lower().endswith(".pdf"):
                    file_path = os.path.join(UPLOAD_DIR, fname)
                    try:
                        with pdfplumber.open(file_path) as pdf:
                            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                        pdf_texts.append(f"[첨부 PDF: {fname}]\n{text}")
                    except Exception as e:
                        pdf_texts.append(f"[첨부 PDF: {fname}]\n(파일 내용 추출 실패: {e})")

    # 원본 메시지 + PDF 내용 합치기
    full_content = message.content
    if pdf_texts:
        full_content += "\n\n" + "\n\n".join(pdf_texts)

    new_message = MessageResponse(
        id=msg_id,
        thread_id=thread_id,
        role=message.role,
        content=[{"type": "text", "text": {"value": full_content}}],
        attachments=attachments,
        created_at=int(time.time())
    )
    messages_db[thread_id].append(new_message)
    return new_message
