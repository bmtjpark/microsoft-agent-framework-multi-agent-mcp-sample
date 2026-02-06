from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..models import WorkflowInput, WorkflowExecutionResponse
from ..client import get_agents_client
import uuid
import time
import asyncio
from typing import Dict, Any, List

router = APIRouter()

# 워크플로우 예시 정의
AVAILABLE_WORKFLOWS = ["hr-onboarding", "research-news", "trip-planner"]

# In-memory storage for execution state
executions_db: Dict[str, Dict[str, Any]] = {}

# Cache for created agent IDs to prevent duplicates
agent_cache: Dict[str, str] = {}

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
    # Check cache first
    if name in agent_cache:
        print(f"Using cached agent: {name} (ID: {agent_cache[name]})")
        return agent_cache[name]
    
    try:
        # Try to find existing agent by name
        assistants = list(client.list())  # Convert to list to handle iterator
        for agent in assistants:
            if agent.name == name:
                print(f"Found existing agent: {name} (ID: {agent.id})")
                agent_cache[name] = agent.id
                return agent.id
    except Exception as e:
        print(f"Error checking existing agents: {e}")
    
    # If not found, create new agent
    try:
        print(f"Creating new agent: {name}")
        agent = client.create_agent(
            name=name,
            instructions=config["instructions"],
            model=config["model"]
        )
        print(f"Created agent: {name} (ID: {agent.id})")
        agent_cache[name] = agent.id
        return agent.id
    except Exception as e:
        print(f"Error creating agent {name}: {e}")
        return None

def get_onboarding_agents(client):
    agent_ids = {}
    for name, config in AGENTS_CONFIG.items():
        aid = ensure_agent(client, name, config)
        if aid:
             agent_ids[name] = aid
    return agent_ids

def run_agent_task(client, agent_id, user_content):
    try:
        thread = client.threads.create()
        client.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_content
        )
        run = client.runs.create(
            thread_id=thread.id,
            agent_id=agent_id
        )
        
        # Simple polling loop
        while run.status in ["queued", "in_progress", "requires_action"]:
            time.sleep(1)
            run = client.runs.get(thread_id=thread.id, run_id=run.id)
            # Simplistic handling: no tool outputs in this workflow currently
            if run.status == "requires_action":
                # If we encountered a tool call we didn't expect, break or fail
                # For this specific HR workflow, we expect simple text.
                print("Unexpected requires_action in HR workflow")
                break
        
        if run.status == "completed":
            messages = client.messages.list(thread_id=thread.id)
            # messages are usually reverse chronological
            # Convert iterator to list to access index 0
            messages_list = list(messages)
            if messages_list:
                 msg_content = "No content"
                 # Check latest message content
                 for c in messages_list[0].content:
                     if c.type == 'text':
                         msg_content = c.text.value
                         break
                 return msg_content
            else:
                 return "No response message found."
        else:
            return f"Error: Run status {run.status}"
            
    except Exception as e:
        return f"Error executing task: {str(e)}"

def process_hr_onboarding_agents(execution_id: str, input_data: dict):
    # Create a fresh client inside the task
    from ..client import get_agents_client
    client = get_agents_client()
    
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
        if "Identity Agent" in agent_ids:
            id_response = run_agent_task(client, agent_ids["Identity Agent"], f"({candidate_name})님을 위한 이메일을 생성해주세요 (한국어로 답변)")
            update_status("in_progress", {
                "agent": "Identity Agent",
                "action": "이메일 생성",
                "details": id_response,
                "timestamp": int(time.time())
            })
        else:
            update_status("in_progress", {
                "agent": "Identity Agent",
                "action": "Error",
                "details": "Agent not found",
                "timestamp": int(time.time())
            })

        # Step 2: IT
        if "IT Agent" in agent_ids:
            it_response = run_agent_task(client, agent_ids["IT Agent"], f"역할: {role}에 따른 장비를 할당해주세요 (한국어로 답변)")
            update_status("in_progress", {
                "agent": "IT Agent",
                "action": "자산 할당",
                "details": it_response,
                "timestamp": int(time.time())
            })

        # Step 3: Training
        if "Training Agent" in agent_ids:
            tr_response = run_agent_task(client, agent_ids["Training Agent"], f"역할: {role}에 따른 교육 과정을 배정해주세요 (한국어로 답변)")
            update_status("completed", {
                "agent": "Training Agent",
                "action": "교육 과정 배정",
                "details": tr_response,
                "timestamp": int(time.time())
            })
        
        # If we reached here, mark completed if not already
        executions_db[execution_id]["status"] = "completed"

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

    # Don't create agents in plan phase - just prepare the plan
    execution_id = str(uuid.uuid4())
    inputs = input_data.inputs
    name = inputs.get("name", "Candidate")
    role = inputs.get("role", "Role")

    plan_text = f"""**{name} ({role})님을 위한 온보딩 계획**

1. **Identity Agent**
   - 작업: 후보자 이름을 기반으로 고유한 회사 이메일 주소를 생성합니다.

2. **IT Agent**
   - 작업: '{role}' 직무에 적합한 하드웨어(노트북, 주변기기)를 결정하고 할당합니다.

3. **Training Agent**
   - 작업: '{role}' 직무를 위한 필수 규정 준수 교육 및 직무별 과정을 배정합니다.

*위의 계획을 검토해 주세요. 진행하려면 '승인'을 클릭하세요.*"""

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
