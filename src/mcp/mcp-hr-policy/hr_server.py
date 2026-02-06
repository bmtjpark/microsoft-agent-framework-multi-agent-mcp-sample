import asyncio
import json
import logging
import os
from typing import Any, Sequence

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hr-server")

# MCP 서버 인스턴스 생성, 이름은 'hr-concierge'
app = Server("hr-concierge")

# 데이터 경로 설정 (정형 데이터와 비정형 데이터 파일)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EMP_PATH = os.path.join(DATA_DIR, "employees.json") # 직원 정보 (JSON)
POLICY_PATH = os.path.join(DATA_DIR, "policy.md")   # 사내 규정 (Markdown)

def load_employees():
    """employees.json 파일에서 직원 데이터를 읽어옵니다."""
    logger.info(f"직원 데이터 로딩 중: {EMP_PATH}")
    with open(EMP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_employees(data):
    """직원 데이터를 employees.json 파일에 저장합니다."""
    logger.info(f"직원 데이터 저장 중: {EMP_PATH}")
    with open(EMP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def search_handbook(query):
    """policy.md 파일에서 키워드 검색을 수행합니다."""
    logger.info(f"규정 검색 시작: '{query}'")
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 매우 간단한 키워드 검색 구현
    results = []
    blocks = content.split("## ") # 헤더 단위로 문서 분할
    for block in blocks:
        if query.lower() in block.lower():
            # 매칭된 블록의 앞부분 200자만 미리보기로 제공
            results.append("## " + block[:200] + "...") 
    
    logger.info(f"검색 결과 {len(results)}건 발견: '{query}'")
    if not results:
        logger.info("해당 쿼리에 대한 규정을 찾을 수 없음")
        return "No specific policy found matching query."
    return "\n\n".join(results)

# ------------------------------------------------------------------------------
# Tools (도구) 정의
# ------------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    """클라이언트에게 제공할 도구(함수) 목록을 정의합니다."""
    logger.info("제공 가능한 도구 목록 조회 요청")
    return [
        Tool(
            name="get_employee_balance",
            description="Check leave balance for an employee. (직원의 잔여 휴가 일수를 조회합니다)",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "Employee ID (직원 ID)"}
                },
                "required": ["employee_id"]
            }
        ),
        Tool(
            name="search_policy_docs",
            description="Search the company handbook for policies. (사내 규정 문서를 키워드로 검색합니다)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords (e.g. 'vacation', 'remote') (검색어)"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="submit_leave_request",
            description="Submit a leave request. (휴가 신청서를 제출하고 잔여 일수를 차감합니다)",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "Employee ID (직원 ID)"},
                    "type": {"type": "string", "enum": ["vacation", "sick", "personal"], "description": "Leave Type (휴가 종류)"},
                    "days": {"type": "number", "description": "Number of days (기간)"}
                },
                "required": ["employee_id", "type", "days"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """클라이언트가 도구 실행을 요청했을 때 호출됩니다."""
    logger.info(f"도구 실행 요청: {name}, 인자: {arguments}")
    
    if name == "get_employee_balance":
        emp_id = arguments["employee_id"]
        data = load_employees()
        emp = next((e for e in data if e["id"] == emp_id), None)
        if emp:
            logger.info(f"휴가 잔액 조회 성공: {emp_id}")
            return [TextContent(type="text", text=json.dumps(emp["leave_balance"], indent=2))]
        logger.warning(f"직원을 찾을 수 없음: {emp_id} (get_employee_balance)")
        return [TextContent(type="text", text="Employee not found.")]

    elif name == "search_policy_docs":
        query = arguments["query"]
        # 비정형 텍스트 데이터 검색
        result = search_handbook(query)
        return [TextContent(type="text", text=result)]

    elif name == "submit_leave_request":
        emp_id = arguments["employee_id"]
        l_type = arguments["type"]
        days = arguments["days"]
        
        data = load_employees()
        emp = next((e for e in data if e["id"] == emp_id), None)
        
        if emp:
            current = emp["leave_balance"].get(l_type, 0)
            if current >= days:
                # 상태 변경: 잔여 휴가 차감 및 신청 내역 추가
                emp["leave_balance"][l_type] -= days
                emp["pending_requests"].append({"type": l_type, "days": days, "status": "Pending"})
                save_employees(data)
                logger.info(f"휴가 신청 완료: {emp_id}, 종류: {l_type}, 기간: {days}일")
                return [TextContent(type="text", text=f"Request submitted. New {l_type} balance: {emp['leave_balance'][l_type]}")]
            else:
                logger.warning(f"잔액 부족으로 신청 실패: {emp_id}, 요청: {days}일, 가능: {current}일")
                return [TextContent(type="text", text=f"Insufficient balance. Available: {current}")]
        logger.warning(f"직원을 찾을 수 없음: {emp_id}")
        return [TextContent(type="text", text="Employee not found.")]

    raise ValueError(f"Unknown tool: {name}")

# ------------------------------------------------------------------------------
# SSE (Server-Sent Events) 전송 계층 설정
# ------------------------------------------------------------------------------

async def handle_sse(request):
    """SSE 연결 요청을 처리합니다."""
    logger.info("새로운 SSE 연결 시도 감지")
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        logger.info("SSE 연결 수립됨. 앱 세션 실행 시작")
        await app.run(streams[0], streams[1], app.create_initialization_options())
    logger.info("SSE 연결 종료됨")
    
    class NoOpResponse:
        async def __call__(self, scope, receive, send):
            pass
    return NoOpResponse()

async def handle_messages(request):
    """클라이언트의 메시지(POST 요청)를 처리합니다."""
    logger.info("POST 메시지 수신됨")
    await sse.handle_post_message(request.scope, request.receive, request._send)
    class NoOpResponse:
        async def __call__(self, scope, receive, send):
            pass
    return NoOpResponse()

sse = SseServerTransport("/messages")
starlette_app = Starlette(routes=[
    Route("/sse", endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"])
])

if __name__ == "__main__":
    import sys
    import uvicorn
    # '--sse' 플래그가 있으면 HTTP/SSE 모드로 실행
    if len(sys.argv) > 1 and sys.argv[1] == "--sse":
        logger.info("서버를 SSE 모드로 시작합니다. 포트: 8003")
        uvicorn.run(starlette_app, host="0.0.0.0", port=8003)
    else:
        # 기본은 STDIO 모드로 실행
        logger.info("서버를 Stdio 모드로 시작합니다")
        asyncio.run(app.run_stdio_async())
