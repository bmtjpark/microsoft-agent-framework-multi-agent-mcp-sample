# Microsoft Agent Framework Based Backend API Specification

This document outlines the API endpoints for a backend server built using the [Microsoft Agent Framework SDK](https://github.com/microsoft/agent-framework). It covers functionalities for Agent management, Thread (conversation) handling, Execution (Runs), and Advanced Workflows.

## Base URL
`http://localhost:8000/api/v1`

## Authentication
Authentication headers (e.g., `Authorization: Bearer <token>`) should be included in requests if security is enabled.

---

## 1. Agents (에이전트 관리)
Manage the lifecycle of AI Agents.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/agents` | List all available agents. |
| **POST** | `/agents` | Create a new agent. <br> **Body:** `{ "name": "string", "model": "string", "instructions": "string", "tools": ["code_interpreter", "file_search"] }` |
| **GET** | `/agents/{agent_id}` | Retrieve details of a specific agent. |
| **PUT** | `/agents/{agent_id}` | Update an agent's configuration. |
| **DELETE** | `/agents/{agent_id}` | Delete an agent. |

## 2. Threads (스레드/대화 관리)
Manage conversation history and context.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/threads` | Create a new conversation thread. <br> **Body:** `{ "metadata": {} }` |
| **GET** | `/threads/{thread_id}` | Get thread details. |
| **DELETE** | `/threads/{thread_id}` | Delete a thread. |
| **GET** | `/threads/{thread_id}/messages` | List all messages in a thread. |
| **POST** | `/threads/{thread_id}/messages` | Add a new user message to the thread. <br> **Body:** `{ "role": "user", "content": "Hello world" }` |

## 3. Runs (실행 및 추론)
Trigger agents to process messages in a thread.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/threads/{thread_id}/runs` | Start a new run with a specific agent. <br> **Body:** `{ "agent_id": "string", "instructions": "optional_override" }` |
| **GET** | `/threads/{thread_id}/runs/{run_id}` | Get the status of a run (queued, in_progress, completed, failed). |
| **POST** | `/threads/{thread_id}/runs/{run_id}/cancel` | Cancel an active run. |
| **POST** | `/threads/{thread_id}/runs/stream` | (Optional) Start a run and stream the response (Server-Sent Events). |

## 4. Workflows (워크플로우/오케스트레이션)
Execute complex, multi-agent workflows defined in the system.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/workflows` | List available workflow definitions (e.g., "hr-onboarding", "research-news"). |
| **POST** | `/workflows/{workflow_name}/execute` | Start a workflow execution. <br> **Body:** `{ "inputs": { "topic": "AI Trends" } }` |
| **GET** | `/workflows/executions/{execution_id}` | Get the status and result of a workflow execution. |

## 5. Files (파일 및 Tool 리소스)
Manage files used by agents (e.g., for Code Interpreter or Search).

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/files` | Upload a file. <br> **Content-Type:** `multipart/form-data` |
| **GET** | `/files` | List uploaded files. |
| **DELETE** | `/files/{file_id}` | Delete a file. |

## 6. System & Telemetry (시스템 상태)
Monitor server health and agent performance.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/health` | Server health check. |
| **GET** | `/telemetry/metrics` | Get basic metrics (e.g., active runs, token usage). |
