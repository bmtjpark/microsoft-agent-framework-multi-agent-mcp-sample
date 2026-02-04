from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- 파일 모델 (File Models) ---
class FileResponse(BaseModel):
    id: str
    filename: str
    purpose: str
    mime_type: str
    created_at: int

# --- 에이전트 모델 (Agent Models) ---
class AgentCreate(BaseModel):
    name: str  # 에이전트 이름
    model: str  # 사용할 모델명 (예: gpt-4o-mini)
    instructions: str  # 에이전트 지시사항 (System Prompt)
    tools: Optional[List[str]] = []  # 사용할 도구 목록 (예: code_interpreter)

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    instructions: Optional[str] = None
    tools: Optional[List[str]] = None

class AgentResponse(BaseModel):
    id: str
    name: str
    model: str
    instructions: str
    tools: List[str]
    created_at: int

# --- 스레드 모델 (Thread Models) ---
class ThreadCreate(BaseModel):
    metadata: Optional[Dict[str, Any]] = None  # 스레드 관련 메타데이터

class ThreadResponse(BaseModel):
    id: str
    metadata: Dict[str, Any]
    created_at: int

# --- 메시지 모델 (Message Models) ---
class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")  # 역할 (user 또는 assistant)
    content: str  # 메시지 내용
    attachments: Optional[List[Dict[str, str]]] = None # 파일 정보 목록 [{id, type}]

class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: List[Any] # Agent Framework에서는 복잡한 콘텐츠(이미지 등)를 포함할 수 있음
    attachments: Optional[List[Dict[str, str]]] = None # [{id, type}]
    created_at: int

# --- 실행 모델 (Run Models) ---
class RunCreate(BaseModel):
    agent_id: str  # 실행할 에이전트 ID
    instructions: Optional[str] = None  # 실행 시 덮어쓸 지시사항 (옵션)

class RunResponse(BaseModel):
    id: str
    thread_id: str
    agent_id: str
    status: str  # 실행 상태 (queued, in_progress, completed, failed 등)
    created_at: int
    last_error: Optional[Any] = None

# --- 워크플로우 모델 (Workflow Models) ---
class WorkflowInput(BaseModel):
    inputs: Dict[str, Any]  # 워크플로우 입력 데이터

class WorkflowExecutionResponse(BaseModel):
    execution_id: str
    workflow_name: str
    status: str
    result: Optional[Any] = None
    inputs: Optional[Dict[str, Any]] = None
    created_at: int

