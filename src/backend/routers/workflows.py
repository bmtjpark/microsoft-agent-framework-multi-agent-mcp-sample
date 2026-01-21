from fastapi import APIRouter, HTTPException
from ..models import WorkflowInput, WorkflowExecutionResponse
import uuid
import time
from typing import Dict, Any

router = APIRouter()

# 워크플로우 예시 정의 (Mock workflows definition)
AVAILABLE_WORKFLOWS = ["hr-onboarding", "research-news", "trip-planner"]
executions_db = {}

# 사용 가능한 워크플로우 목록 조회 (List available workflows)
@router.get("/workflows")
async def list_workflows():
    return {"workflows": AVAILABLE_WORKFLOWS}

# 워크플로우 실행 (Execute a workflow)
@router.post("/workflows/{workflow_name}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(workflow_name: str, input_data: WorkflowInput):
    if workflow_name not in AVAILABLE_WORKFLOWS:
        raise HTTPException(status_code=404, detail="워크플로우를 찾을 수 없습니다.")
    
    execution_id = str(uuid.uuid4())
    execution = WorkflowExecutionResponse(
        execution_id=execution_id,
        workflow_name=workflow_name,
        status="running",
        result=None
    )
    executions_db[execution_id] = execution
    
    # 실제 시나리오에서는 여기서 비동기 작업이나 오케스트레이션을 시작합니다.
    return execution

# 워크플로우 실행 상태 조회 (Get execution status)
@router.get("/workflows/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_execution(execution_id: str):
    if execution_id not in executions_db:
        raise HTTPException(status_code=404, detail="실행 정보를 찾을 수 없습니다.")
    
    # 완료 상태 시뮬레이션 (Mock completion)
    execution = executions_db[execution_id]
    if execution.status == "running":
        execution.status = "completed"
        execution.result = {"message": f"워크플로우 '{execution.workflow_name}'가 성공적으로 완료되었습니다."}
        
    return execution
