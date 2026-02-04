from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models import FileResponse
from ..client import get_inference_client
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
    
    client = get_inference_client()
    try:
        # Upload to Azure using OpenAI compatibility
        with open(file_path, "rb") as f:
            uploaded_file = client.files.create(file=f, purpose=purpose)
        
        return FileResponse(
            id=uploaded_file.id,
            filename=uploaded_file.filename,
            purpose=uploaded_file.purpose,
            mime_type="application/octet-stream", # Azure might not return mime_type
            created_at=uploaded_file.created_at
        )
    except Exception as e:
        # Clean up local file on failure if we want
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Azure upload failed: {str(e)}")

# 파일 목록 조회 (List files)
@router.get("/files", response_model=list[FileResponse])
async def list_files():
    client = get_inference_client()
    try:
        # Query Azure for files
        files_data = client.files.list()
        
        response_files = []
        for f in files_data.data:
            # Filter by intention if needed, but endpoint lists all
            response_files.append(FileResponse(
                id=f.id,
                filename=f.filename,
                purpose=f.purpose,
                mime_type="application/octet-stream",
                created_at=f.created_at
            ))
        return response_files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List files failed: {str(e)}")

# 파일 삭제 (Delete a file)
@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    client = get_inference_client()
    try:
        client.files.delete(file_id)
        return {"message": "파일이 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

