from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models import FileResponse
import uuid
import time
import shutil
import os

router = APIRouter()

UPLOAD_DIR = "uploads"
files_db = {}

# 업로드 디렉토리가 없으면 생성 (Ensure upload directory exists)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 파일 업로드 (Upload a file)
@router.post("/files", response_model=FileResponse)
async def upload_file(file: UploadFile = File(...), purpose: str = "agents"):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    # 파일 저장
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    new_file = FileResponse(
        id=file_id,
        filename=file.filename,
        purpose=purpose,
        created_at=int(time.time())
    )
    files_db[file_id] = new_file
    return new_file

# 파일 목록 조회 (List files)
@router.get("/files", response_model=list[FileResponse])
async def list_files():
    return list(files_db.values())

# 파일 삭제 (Delete a file)
@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    
    # 실제 앱에서는 디스크에서 파일도 삭제해야 합니다.
    # file_info = files_db[file_id]
    # os.remove(...)
    
    del files_db[file_id]
    return {"message": "파일이 성공적으로 삭제되었습니다."}
