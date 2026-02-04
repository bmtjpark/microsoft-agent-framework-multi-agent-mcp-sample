from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict
import os
from ..models import AgentCreate, AgentUpdate, AgentResponse
from ..client import get_inference_client
from ..database import agent_active_threads

router = APIRouter()

def _map_row_agent_to_response(assistant) -> AgentResponse:
    # OpenAI Assistant object mapping
    tools_list = []
    if assistant.tools:
        for t in assistant.tools:
            if hasattr(t, "type"):
                tools_list.append(t.type)
            elif isinstance(t, dict):
                 tools_list.append(t.get("type", "unknown"))

    return AgentResponse(
        id=assistant.id,
        name=assistant.name or "Unnamed Agent",
        model=assistant.model,
        instructions=assistant.instructions or "",
        tools=tools_list,
        created_at=assistant.created_at
    )

# 에이전트 목록 조회 (List all agents)
@router.get("/agents", response_model=List[AgentResponse])
async def list_agents():
    client = get_inference_client()
    try:
        # OpenAI style listing
        assistants = client.beta.assistants.list(order="desc", limit=50)
        
        response_agents = []
        for agent in assistants.data:
            response_agents.append(_map_row_agent_to_response(agent))
                
        return response_agents
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"에이전트 목록 조회 실패: {str(e)}")

# 에이전트 생성 (Create a new agent)
@router.post("/agents", response_model=AgentResponse)
async def create_agent(agent: AgentCreate):
    client = get_inference_client()
    try:
        # Convert tool names to OpenAI tool objects
        tools_objs = []
        if agent.tools:
            for t_name in agent.tools:
                if t_name == "code_interpreter":
                    tools_objs.append({"type": "code_interpreter"})
                elif t_name == "file_search": 
                     tools_objs.append({"type": "file_search"})
        
        # .env에서 모델명 가져오기, 없으면 요청받은 model 사용
        env_model = os.getenv("AZURE_MODEL_DEPLOYMENT_NAME")
        target_model = env_model if env_model else agent.model

        created_agent = client.beta.assistants.create(
            name=agent.name,
            model=target_model,
            instructions=agent.instructions,
            tools=tools_objs
        )
        
        return _map_row_agent_to_response(created_agent)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"에이전트 생성 실패: {str(e)}")

# 특정 에이전트 조회 (Get a specific agent)
@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    client = get_inference_client()
    try:
        agent = client.beta.assistants.retrieve(agent_id)
        return _map_row_agent_to_response(agent)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"에이전트를 찾을 수 없습니다: {str(e)}")

# 에이전트 삭제 (Delete an agent)
@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    client = get_inference_client()
    try:
        client.beta.assistants.delete(agent_id)
        return {"message": "에이전트가 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"에이전트 삭제 실패: {str(e)}")

# 에이전트별 최신 스레드 조회 (Get active thread for agent)
@router.get("/agents/{agent_id}/thread")
async def get_agent_thread(agent_id: str):
    thread_id = agent_active_threads.get(agent_id)
    if not thread_id:
        return {"thread_id": None}
    return {"thread_id": thread_id}

# 에이전트별 최신 스레드 설정 (Set active thread for agent)
@router.post("/agents/{agent_id}/thread")
async def set_agent_thread(agent_id: str, payload: Dict[str, str] = Body(...)):
    thread_id = payload.get("thread_id")
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")
    
    agent_active_threads[agent_id] = thread_id
    return {"thread_id": thread_id, "agent_id": agent_id}

