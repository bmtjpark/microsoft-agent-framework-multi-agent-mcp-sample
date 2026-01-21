from fastapi import APIRouter, HTTPException
from typing import List
from ..models import AgentCreate, AgentUpdate, AgentResponse
from ..database import agents_db
import uuid
import time

router = APIRouter()

# 에이전트 목록 조회 (List all agents)
@router.get("/agents", response_model=List[AgentResponse])
async def list_agents():
    return list(agents_db.values())

# 에이전트 생성 (Create a new agent)
@router.post("/agents", response_model=AgentResponse)
async def create_agent(agent: AgentCreate):
    agent_id = str(uuid.uuid4())
    new_agent = AgentResponse(
        id=agent_id,
        name=agent.name,
        model=agent.model,
        instructions=agent.instructions,
        tools=agent.tools or [],
        created_at=int(time.time())
    )
    agents_db[agent_id] = new_agent
    return new_agent

# 특정 에이전트 조회 (Get a specific agent)
@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")
    return agents_db[agent_id]

# 에이전트 수정 (Update an agent)
@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, agent_update: AgentUpdate):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")
    
    current_agent = agents_db[agent_id]
    updated_data = agent_update.dict(exclude_unset=True)
    
    # 필드 업데이트 (Update fields)
    updated_agent = current_agent.copy(update=updated_data)
    agents_db[agent_id] = updated_agent
    return updated_agent

# 에이전트 삭제 (Delete an agent)
@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")
    del agents_db[agent_id]
    return {"message": "에이전트가 성공적으로 삭제되었습니다."}
