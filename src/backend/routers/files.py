from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models import FileResponse
from ..client import get_agents_client
import shutil
import os
import uuid
import time

router = APIRouter()

UPLOAD_DIR = "uploads"

# 업로드 디렉토리가 없으면 생성 (Ensure upload directory exists)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 파일 업로드 (Upload a file)
@router.post("/files", response_model=FileResponse)
async def upload_file(file: UploadFile = File(...), purpose: str = "assistants"):
    # Generate a temp local path to handle the file stream
    file_id_temp = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id_temp}_{file.filename}")
    
    # Save locally first
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    client = get_agents_client()
    try:
        # Upload using Agents SDK
        with open(file_path, "rb") as f:
            uploaded_file = client.files.upload(file=f, purpose=purpose)
        
        created_at_ts = 0
        if hasattr(uploaded_file, "created_at"):
             if isinstance(uploaded_file.created_at, int):
                 created_at_ts = uploaded_file.created_at
             elif hasattr(uploaded_file.created_at, "timestamp"):
                 created_at_ts = int(uploaded_file.created_at.timestamp())

        return FileResponse(
            id=uploaded_file.id,
            filename=uploaded_file.filename,
            purpose=uploaded_file.purpose,
            mime_type="application/octet-stream", # Azure might not return mime_type
            created_at=created_at_ts
        )
    except Exception as e:
        # Clean up local file on failure if we want
        if os.path.exists(file_path):
            os.remove(file_path)
            
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Azure upload failed: {str(e)}")

# 파일 목록 조회 (List files)
@router.get("/files", response_model=list[FileResponse])
async def list_files():
    client = get_agents_client()
    try:
        # Query Azure for files
        files_data = client.files.list()
        
        response_files = []
        # list context usually returns a page/iterator
        
        # Determine if it's an iterator or object with 'data'
        iterator = files_data
        if hasattr(files_data, "data"):
             iterator = files_data.data
             
        for f in iterator:
            created_at_ts = 0
            if hasattr(f, "created_at"):
                if isinstance(f.created_at, int):
                    created_at_ts = f.created_at
                elif hasattr(f.created_at, "timestamp"):
                    created_at_ts = int(f.created_at.timestamp())
        
            response_files.append(FileResponse(
                id=f.id,
                filename=f.filename,
                purpose=f.purpose,
                mime_type="application/octet-stream",
                created_at=created_at_ts
            ))
        return response_files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List files failed: {str(e)}")

# 파일 삭제 (Delete a file)
@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    client = get_agents_client()
    try:
        client.files.delete(file_id)
        return {"message": "파일이 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

