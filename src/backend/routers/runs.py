from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from ..models import RunCreate, RunResponse
from ..client import get_agents_client
from ..mcp_manager import execute_mcp_tool_call
import time
import asyncio
import json

router = APIRouter()

# 실행 생성 (Create a run)
@router.post("/threads/{thread_id}/runs", response_model=RunResponse)
async def create_run(thread_id: str, run_input: RunCreate):
    client = get_agents_client()
    try:
        # Note: Azure AI Agents SDK uses 'agent_id', not 'assistant_id'
        kwargs = {
            "thread_id": thread_id,
            "agent_id": run_input.agent_id
        }
        if run_input.instructions:
            kwargs["instructions"] = run_input.instructions

        run = client.runs.create(**kwargs)
        
        created_at_ts = 0
        if hasattr(run, "created_at"):
             if isinstance(run.created_at, int):
                 created_at_ts = run.created_at
             elif hasattr(run.created_at, "timestamp"):
                 created_at_ts = int(run.created_at.timestamp())
        
        # Check if attribute is agent_id or assistant_id
        agent_id_val = getattr(run, "agent_id", None) or getattr(run, "assistant_id", None)

        return RunResponse(
            id=run.id,
            thread_id=run.thread_id,
            agent_id=agent_id_val,
            status=run.status,
            created_at=created_at_ts,
            last_error=None
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"실행 생성 실패: {str(e)}")

# 실행 상태 조회 (Get run status) - Polling endpoint
@router.get("/threads/{thread_id}/runs/{run_id}", response_model=RunResponse)
async def get_run(thread_id: str, run_id: str):
    client = get_agents_client()
    try:
        run = client.runs.get(thread_id=thread_id, run_id=run_id)
        
        # Handle 'requires_action' (Tool Calls)
        if run.status == "requires_action" and run.required_action and run.required_action.submit_tool_outputs:
            tool_outputs = []
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            
            for tool_call in tool_calls:
                fn_name = tool_call.function.name
                fn_args = tool_call.function.arguments
                
                # Check if it's an MCP tool (mapped by prefix)
                if "__" in fn_name:
                    try:
                        # Arguments might be a string or already a dict depending on SDK version
                        if isinstance(fn_args, str):
                            args_dict = json.loads(fn_args)
                        else:
                            args_dict = fn_args
                            
                        # execute_mcp_tool_call expects fn_name and dict arguments
                        output_str = await execute_mcp_tool_call(fn_name, args_dict)
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": str(output_str)
                        })
                    except Exception as e:
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": f"Error fulfilling tool call: {str(e)}"
                        })
            
            # Submit outputs if we processed any MCP tools
            if tool_outputs:
                client.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs
                )
                # Wait briefly to let the run progress
                time.sleep(0.5)
                run = client.runs.get(thread_id=thread_id, run_id=run_id)

        last_error = None
        if run.last_error:
            # Handle object vs dict
            if isinstance(run.last_error, dict):
                 last_error = {"code": run.last_error.get("code"), "message": run.last_error.get("message")}
            else:
                 last_error = {"code": run.last_error.code, "message": run.last_error.message}

        created_at_ts = 0
        if hasattr(run, "created_at"):
             if isinstance(run.created_at, int):
                 created_at_ts = run.created_at
             elif hasattr(run.created_at, "timestamp"):
                 created_at_ts = int(run.created_at.timestamp())
        
        # Check if attribute is agent_id or assistant_id
        agent_id_val = getattr(run, "agent_id", None) or getattr(run, "assistant_id", None)

        return RunResponse(
            id=run.id,
            thread_id=run.thread_id,
            agent_id=agent_id_val,
            status=run.status,
            created_at=created_at_ts,
            last_error=last_error
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=404, detail=f"실행 조회 실패: {str(e)}")

# 실행 취소 (Cancel run)
@router.post("/threads/{thread_id}/runs/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(thread_id: str, run_id: str):
    client = get_agents_client()
    try:
        client.runs.cancel(thread_id=thread_id, run_id=run_id)
        # Return updated status
        run = client.runs.get(thread_id=thread_id, run_id=run_id)

        created_at_ts = 0
        if hasattr(run, "created_at"):
             if isinstance(run.created_at, int):
                 created_at_ts = run.created_at
             elif hasattr(run.created_at, "timestamp"):
                 created_at_ts = int(run.created_at.timestamp())
        
        # Check if attribute is agent_id or assistant_id
        agent_id_val = getattr(run, "agent_id", None) or getattr(run, "assistant_id", None)

        return RunResponse(
            id=run.id,
            thread_id=run.thread_id,
            agent_id=agent_id_val,
            status=run.status,
            created_at=created_at_ts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"취소 실패: {str(e)}")

