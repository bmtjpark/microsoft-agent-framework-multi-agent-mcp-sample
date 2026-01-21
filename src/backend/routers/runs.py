from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from ..models import RunCreate, RunResponse, MessageResponse
from ..database import runs_db, messages_db, agents_db
import uuid
import time
import asyncio
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
try:
    from openai import NotFoundError, AzureOpenAI
except ImportError:
    NotFoundError = Exception
    AzureOpenAI = None

router = APIRouter()

project_client = None

def get_project_client():
    global project_client
    if not project_client:
        conn_str = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
        if conn_str:
            try:
                # Assuming the connection string in .env is actually the endpoint URL
                project_client = AIProjectClient(
                    endpoint=conn_str,
                    credential=DefaultAzureCredential()
                )
            except Exception as e:
                print(f"Failed to initialize AIProjectClient: {e}")
    return project_client

def get_azure_openai_client(client):
    """
    Manually retrieve AzureOpenAI client from Project connections
    to bypass potential Project Endpoint routing issues.
    """
    try:
        aoai_target = None
        
        # Cache connections to list since iterator might be consumed
        all_connections = list(client.connections.list())
        
        # Log for debugging
        print(f"DEBUG: Found {len(all_connections)} connections.")
        for c in all_connections:
            print(f"DEBUG: Connection Name='{c.name}', Type='{getattr(c, 'type', 'Unknown')}', Target='{getattr(c, 'target', 'None')}'")

        # List connections to find AOAI
        for c in all_connections:
            # Check for typical type names (enum or string)
            c_type = str(getattr(c, 'type', ''))
            # Check for string 'AzureOpenAI' or check if it matches the enum value string
            if 'AzureOpenAI' in c_type or 'AZURE_OPEN_AI' in c_type:
                aoai_target = getattr(c, 'target', None)
                if aoai_target:
                    print(f"DEBUG: Found target via Type match: {aoai_target}")
                    break
        
        if not aoai_target:
             # Fallback: Check name
             for c in all_connections:
                 if 'openai' in getattr(c, 'name', '').lower():
                      aoai_target = getattr(c, 'target', None)
                      if aoai_target:
                          print(f"DEBUG: Found target via Name match: {aoai_target}")
                          break
        
        if not aoai_target:
            raise Exception("No Azure OpenAI connection found in Project.")
            
        token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
        
        if AzureOpenAI is None:
            raise Exception("openai package not installed or AzureOpenAI not available")

        return AzureOpenAI(
            azure_endpoint=aoai_target,
            azure_ad_token_provider=token_provider,
            api_version="2024-06-01"
        )
    except Exception as e:
        print(f"Error resolving AOAI client: {e}")
        # Fallback to the project's own method if our manual resolution fails
        return client.get_openai_client()

async def process_run(run_id: str):
    print(f"Processing run {run_id}...")
    run = runs_db.get(run_id)
    if not run:
        return
    
    run.status = "in_progress"
    
    try:
        agent = agents_db.get(run.agent_id)
        if not agent:
             print(f"Agent {run.agent_id} not found")
             run.status = "failed"
             return
             
        thread_messages = messages_db.get(run.thread_id, [])
        
        # Build prompt
        messages = [
            {"role": "system", "content": agent.instructions}
        ]
        
        for msg in thread_messages:
            # Handle list content (from our model) to string
            content_str = ""
            if isinstance(msg.content, list):
                for part in msg.content:
                    if part.get("type") == "text":
                        content_str += part["text"]["value"]
            else:
                content_str = str(msg.content)
            
            messages.append({"role": msg.role, "content": content_str})
            
        # Call LLM
        client = get_project_client()
        if not client:
             raise Exception("AI Project Client not initialized. Check .env")
             
        # Use OpenAI client resolved from connections
        # Do not use 'with client:' as it closes the global singleton transport
        chat_client = get_azure_openai_client(client)
        response = chat_client.chat.completions.create(
            model=agent.model, # e.g. "gpt-4o"
            messages=messages
        )
        
        completion_text = response.choices[0].message.content
        
        new_message = MessageResponse(
            id=str(uuid.uuid4()),
            thread_id=run.thread_id,
            role="assistant",
            content=[{"type": "text", "text": {"value": completion_text}}],
            created_at=int(time.time())
        )
        
        if run.thread_id not in messages_db:
            messages_db[run.thread_id] = []
        messages_db[run.thread_id].append(new_message)
        
        run.status = "completed"
        print(f"Run {run_id} completed successfully.")
        
    except NotFoundError as e:
        error_msg = f"Model '{agent.model}' not found in Azure AI Project. Please verify the deployment name."
        print(f"Run {run_id} failed: {error_msg}")
        run.status = "failed"
        run.last_error = {"code": "model_not_found", "message": error_msg}

    except Exception as e:
        print(f"Run {run_id} failed: {e}")
        run.status = "failed"
        run.last_error = {"code": "internal_error", "message": str(e)}

# 실행 생성 (Create a Run)
@router.post("/threads/{thread_id}/runs", response_model=RunResponse)
async def create_run(thread_id: str, run_req: RunCreate, background_tasks: BackgroundTasks):
    # 실제 앱에서는 agent_id가 존재하는지 검증해야 합니다.
    run_id = str(uuid.uuid4())
    new_run = RunResponse(
        id=run_id,
        thread_id=thread_id,
        agent_id=run_req.agent_id,
        status="queued",  # 초기 상태는 'queued'
        created_at=int(time.time())
    )
    runs_db[run_id] = new_run
    
    # 백그라운드 처리 실행
    background_tasks.add_task(process_run, run_id)

    return new_run

# 실행 상태 조회 (Get Run Status)
@router.get("/threads/{thread_id}/runs/{run_id}", response_model=RunResponse)
async def get_run(thread_id: str, run_id: str):
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail="실행 정보를 찾을 수 없습니다.")
    
    run = runs_db[run_id]
    # process_run handles status updates now
    
    return run

# 실행 취소 (Cancel Run)
@router.post("/threads/{thread_id}/runs/{run_id}/cancel")
async def cancel_run(thread_id: str, run_id: str):
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail="실행 정보를 찾을 수 없습니다.")
    
    runs_db[run_id].status = "cancelled"
    return {"status": "cancelled"}

# 스트리밍 실행 (Stream Run)
@router.post("/threads/{thread_id}/runs/stream")
async def stream_run(thread_id: str, run_req: RunCreate):
    # 스트리밍 응답 시뮬레이션 (Mock streaming response)
    async def event_generator():
        yield f"data: {{\"status\": \"queued\"}}\n\n"
        await asyncio.sleep(1)
        yield f"data: {{\"status\": \"in_progress\"}}\n\n"
        await asyncio.sleep(1)
        yield f"data: {{\"content\": \"에이전트 {run_req.agent_id}의 스트리밍 응답입니다.\"}}\n\n"
        await asyncio.sleep(1)
        yield f"data: {{\"status\": \"completed\"}}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
