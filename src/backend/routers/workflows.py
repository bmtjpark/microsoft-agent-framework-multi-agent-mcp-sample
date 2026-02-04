from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..models import WorkflowInput, WorkflowExecutionResponse
from ..client import get_inference_client
import uuid
import time
import asyncio
from typing import Dict, Any, List

router = APIRouter()

# 워크플로우 예시 정의
AVAILABLE_WORKFLOWS = ["hr-onboarding", "research-news", "trip-planner"]

# In-memory storage for execution state
executions_db: Dict[str, Dict[str, Any]] = {}

# Agent Definitions
AGENTS_CONFIG = {
    "Identity Agent": {
        "instructions": "You are an Identity Management Agent. When given a candidate name, generate a company email address for them in the format firstname.lastname@company.com. Return only the email address. 답변은 반드시 한국어로 작성해 주세요.",
        "model": "gpt-4o-mini"
    },
    "IT Agent": {
        "instructions": "You are an IT Coordinator Agent. Assign laptops based on role. Developers get MacBook Pro, others get Dell XPS. Return only the assigned device name. 답변은 반드시 한국어로 작성해 주세요.",
        "model": "gpt-4o-mini"
    },
    "Training Agent": {
        "instructions": "You are a Training Coordinator Agent. Assign courses based on role. Developers get 'Security Coding', others get 'Company Culture'. Return the list of courses. 답변은 반드시 한국어로 작성해 주세요.",
        "model": "gpt-4o-mini"
    }
}

def ensure_agent(client, name, config):
    try:
        assistants = client.beta.assistants.list(limit=50)
        for agent in assistants.data:
            if agent.name == name:
                return agent.id
    except:
        pass
    
    agent = client.beta.assistants.create(
        name=name,
        instructions=config["instructions"],
        model=config["model"]
    )
    return agent.id

def get_onboarding_agents(client):
    agent_ids = {}
    for name, config in AGENTS_CONFIG.items():
        agent_ids[name] = ensure_agent(client, name, config)
    return agent_ids

def run_agent_task(client, agent_id, user_content):
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_content
    )
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=agent_id
    )
    
    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        # messages are in reverse chronological order
        msg_content = messages.data[0].content[0].text.value
        return msg_content
    else:
        return f"Error: {run.status}"

def process_hr_onboarding_agents(execution_id: str, input_data: dict):
    client = get_inference_client()
    agent_ids = get_onboarding_agents(client)
    
    candidate_name = input_data.get("name", "Unknown")
    role = input_data.get("role", "Employee")

    def update_status(status, step_data=None):
        if execution_id in executions_db:
            executions_db[execution_id]["status"] = status
            if step_data:
                current_result = executions_db[execution_id].get("result") or {"steps": []}
                if "steps" not in current_result:
                    current_result["steps"] = []
                current_result["steps"].append(step_data)
                executions_db[execution_id]["result"] = current_result

    try:
        # Step 1: Identity
        update_status("in_progress")
        id_response = run_agent_task(client, agent_ids["Identity Agent"], f"({candidate_name})님을 위한 이메일을 생성해주세요 (한국어로 답변)")
        update_status("in_progress", {
            "agent": "Identity Agent",
            "action": "이메일 생성",
            "details": id_response,
            "timestamp": int(time.time())
        })

        # Step 2: IT
        it_response = run_agent_task(client, agent_ids["IT Agent"], f"역할: {role}에 따른 장비를 할당해주세요 (한국어로 답변)")
        update_status("in_progress", {
            "agent": "IT Agent",
            "action": "자산 할당",
            "details": it_response,
            "timestamp": int(time.time())
        })

        # Step 3: Training
        tr_response = run_agent_task(client, agent_ids["Training Agent"], f"역할: {role}에 따른 교육 과정을 배정해주세요 (한국어로 답변)")
        update_status("completed", {
            "agent": "Training Agent",
            "action": "교육 과정 배정",
            "details": tr_response,
            "timestamp": int(time.time())
        })

    except Exception as e:
        print(f"Error in onboarding workflow: {e}")
        update_status("failed", {
            "agent": "System",
            "action": "Error",
            "details": str(e),
            "timestamp": int(time.time())
        })

@router.get("/workflows")
async def list_workflows():
    return {"workflows": AVAILABLE_WORKFLOWS}

@router.post("/workflows/{workflow_name}/plan", response_model=WorkflowExecutionResponse)
async def plan_workflow(workflow_name: str, input_data: WorkflowInput):
    if workflow_name != "hr-onboarding":
         raise HTTPException(status_code=400, detail="Planning only supported for hr-onboarding")

    # Ensure agents exist (pre-check)
    agent_ids = {}
    try:
        client = get_inference_client()
        agent_ids = get_onboarding_agents(client)
    except Exception as e:
        print(f"Warning: agent init failed: {e}")

    execution_id = str(uuid.uuid4())
    inputs = input_data.inputs
    name = inputs.get("name", "Candidate")
    role = inputs.get("role", "Role")

    id_id = agent_ids.get("Identity Agent", "N/A")
    it_id = agent_ids.get("IT Agent", "N/A")
    tr_id = agent_ids.get("Training Agent", "N/A")

    plan_text = f"""**{name} ({role})님을 위한 온보딩 계획**

1. **Identity Agent** (ID: `{id_id}`)
   - 작업: 후보자 이름을 기반으로 고유한 회사 이메일 주소를 생성합니다.

2. **IT Agent** (ID: `{it_id}`)
   - 작업: '{role}' 직무에 적합한 하드웨어(노트북, 주변기기)를 결정하고 할당합니다.

3. **Training Agent** (ID: `{tr_id}`)
   - 작업: '{role}' 직무를 위한 필수 규정 준수 교육 및 직무별 과정을 배정합니다.

*위의 할당된 에이전트와 작업을 검토해 주세요. 진행하려면 '승인'을 클릭하세요.*"""

    initial_state = {
        "execution_id": execution_id,
        "workflow_name": workflow_name,
        "status": "waiting_for_approval",
        "result": {"steps": [], "plan": plan_text},
        "created_at": int(time.time()),
        "inputs": inputs # Store inputs for later execution
    }
    executions_db[execution_id] = initial_state
    
    return WorkflowExecutionResponse(**initial_state)

@router.post("/workflows/executions/{execution_id}/approve", response_model=WorkflowExecutionResponse)
async def approve_workflow(execution_id: str, background_tasks: BackgroundTasks):
    if execution_id not in executions_db:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = executions_db[execution_id]
    if execution["status"] != "waiting_for_approval":
        raise HTTPException(status_code=400, detail="Workflow not waiting for approval")
    
    execution["status"] = "queued"
    inputs = execution.get("inputs", {})
    
    background_tasks.add_task(process_hr_onboarding_agents, execution_id, inputs)
    
    return WorkflowExecutionResponse(**execution)

@router.post("/workflows/{workflow_name}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(workflow_name: str, input_data: WorkflowInput, background_tasks: BackgroundTasks):
    # Backward compatibility or direct execution for others
    if workflow_name == "hr-onboarding":
        return await plan_workflow(workflow_name, input_data)

    if workflow_name not in AVAILABLE_WORKFLOWS:
        raise HTTPException(status_code=404, detail="워크플로우를 찾을 수 없습니다.")
    
    execution_id = str(uuid.uuid4())
    
    # Initialize state
    initial_state = {
        "execution_id": execution_id,
        "workflow_name": workflow_name,
        "status": "queued",
        "result": {"steps": []},
        "created_at": int(time.time()),
        "inputs": input_data.inputs
    }
    executions_db[execution_id] = initial_state
    
    # Generic mock for others
    background_tasks.add_task(lambda eid: time.sleep(1), execution_id)
        
    return WorkflowExecutionResponse(**initial_state)

@router.get("/workflows/executions", response_model=List[WorkflowExecutionResponse])
async def list_executions():
    return [WorkflowExecutionResponse(**data) for data in executions_db.values()]

@router.get("/workflows/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_execution(execution_id: str):
    if execution_id not in executions_db:
        raise HTTPException(status_code=404, detail="실행 정보를 찾을 수 없습니다.")
    
    data = executions_db[execution_id]
    return WorkflowExecutionResponse(**data)

@router.delete("/workflows/executions/{execution_id}")
async def delete_execution(execution_id: str):
    if execution_id not in executions_db:
        raise HTTPException(status_code=404, detail="실행 정보를 찾을 수 없습니다.")
    
    del executions_db[execution_id]
    return {"message": "실행 기록이 성공적으로 삭제되었습니다."}
