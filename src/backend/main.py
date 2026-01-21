from fastapi import FastAPI
from .routers import agents, threads, runs, workflows, files, system
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 로직 (Startup logic)
    print("Agent Framework API 서버를 시작합니다...")
    print("API 문서 (Swagger UI): http://localhost:8000/docs")
    print("건강 상태 확인 (Health Check): http://localhost:8000/api/v1/health")
    # 필요시 SDK 클라이언트 초기화 (Initialize SDK clients here if needed)
    yield
    # 종료 로직 (Shutdown logic)
    print("서버를 종료합니다...")

app = FastAPI(
    title="Microsoft Agent Framework API",
    description="AI 에이전트, 스레드 및 워크플로우 관리를 위한 백엔드 API",
    version="1.0.0",
    lifespan=lifespan
)

# 라우터 포함 (Include Routers)
app.include_router(agents.router, tags=["Agents"], prefix="/api/v1")
app.include_router(threads.router, tags=["Threads"], prefix="/api/v1")
app.include_router(runs.router, tags=["Runs"], prefix="/api/v1")
app.include_router(workflows.router, tags=["Workflows"], prefix="/api/v1")
app.include_router(files.router, tags=["Files"], prefix="/api/v1")
app.include_router(system.router, tags=["System"], prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)
