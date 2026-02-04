from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from ..models import RunCreate, RunResponse
from ..client import get_inference_client
import time
import asyncio

router = APIRouter()

# 실행 생성 (Create a run)
@router.post("/threads/{thread_id}/runs", response_model=RunResponse)
async def create_run(thread_id: str, run_input: RunCreate):
    client = get_inference_client()
    try:
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=run_input.agent_id,
            instructions=run_input.instructions
            # additional_instructions can be mapped if needed
        )
        return RunResponse(
            id=run.id,
            thread_id=run.thread_id,
            agent_id=run.assistant_id,
            status=run.status,
            created_at=run.created_at,
            last_error=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실행 생성 실패: {str(e)}")

# 실행 상태 조회 (Get run status) - Polling endpoint
@router.get("/threads/{thread_id}/runs/{run_id}", response_model=RunResponse)
async def get_run(thread_id: str, run_id: str):
    client = get_inference_client()
    try:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        
        last_error = None
        if run.last_error:
            last_error = {"code": run.last_error.code, "message": run.last_error.message}

        return RunResponse(
            id=run.id,
            thread_id=run.thread_id,
            agent_id=run.assistant_id,
            status=run.status,
            created_at=run.created_at,
            last_error=last_error
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"실행 조회 실패: {str(e)}")

# 실행 취소 (Cancel run)
@router.post("/threads/{thread_id}/runs/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(thread_id: str, run_id: str):
    client = get_inference_client()
    try:
        client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run_id)
        # Return updated status
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        return RunResponse(
            id=run.id,
            thread_id=run.thread_id,
            agent_id=run.assistant_id,
            status=run.status,
            created_at=run.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"취소 실패: {str(e)}")

