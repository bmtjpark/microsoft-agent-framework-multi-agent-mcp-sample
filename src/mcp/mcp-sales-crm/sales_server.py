import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Sequence

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource, Resource

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sales-server")

# MCP 서버 인스턴스 생성, 이름은 'sales-crm'
app = Server("sales-crm")

# Mock 데이터 경로 설정 (customers.json 파일을 사용)
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "customers.json")

def load_data():
    """customers.json 파일에서 데이터를 읽어옵니다."""
    logger.info(f"고객 데이터 로딩 중: {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    """데이터를 customers.json 파일에 저장합니다."""
    logger.info(f"고객 데이터 저장 중: {DATA_PATH}")
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ------------------------------------------------------------------------------
# Tools (도구) 정의
# ------------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    """클라이언트에게 제공할 도구(함수) 목록을 정의합니다."""
    logger.info("제공 가능한 도구 목록 조회 요청")
    return [
        Tool(
            name="get_customer_profile",
            description="Retrieve customer profile including revenue and risk status. (고객의 기본 프로필 정보를 조회합니다)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cust_name_or_id": {"type": "string", "description": "Client Name or ID (고객명 또는 ID)"}
                },
                "required": ["cust_name_or_id"]
            }
        ),
        Tool(
            name="get_recent_interactions",
            description="Get a list of recent notes/emails/meetings for a customer. (고객의 최근 상담/미팅 이력을 조회합니다)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cust_name_or_id": {"type": "string", "description": "Client Name or ID (고객명 또는 ID)"}
                },
                "required": ["cust_name_or_id"]
            }
        ),
        Tool(
            name="add_meeting_note",
            description="Log a new meeting note for a customer. (새로운 미팅 노트를 DB에 추가합니다)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cust_id": {"type": "string", "description": "Exact Customer ID (정확한 고객 ID)"},
                    "note": {"type": "string", "description": "Note Content (노트 내용)"},
                    "date": {"type": "string", "description": "Date YYYY-MM-DD (날짜)"}
                },
                "required": ["cust_id", "note"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """클라이언트가 도구 실행을 요청했을 때 호출됩니다."""
    logger.info(f"도구 실행 요청: {name}, 인자: {arguments}")
    data = load_data()
    
    if name == "get_customer_profile":
        query = arguments["cust_name_or_id"].lower()
        # 간단한 검색 구현 (이름 포함 여부 또는 ID 일치 여부)
        customer = next((c for c in data if query in c["name"].lower() or query == c["id"].lower()), None)
        
        if customer:
            logger.info(f"고객 프로필 조회 성공: {query}")
            # 프로필 조회 시 상호작용(interactions) 내역은 제외하고 반환 (너무 길어서)
            profile = {k: v for k, v in customer.items() if k != "interactions"}
            return [TextContent(type="text", text=json.dumps(profile, indent=2, ensure_ascii=False))]
        logger.warning(f"고객을 찾을 수 없음: {query} (get_customer_profile)")
        return [TextContent(type="text", text=f"Customer '{query}' not found.")]

    elif name == "get_recent_interactions":
        query = arguments["cust_name_or_id"].lower()
        customer = next((c for c in data if query in c["name"].lower() or query == c["id"].lower()), None)
        
        if customer:
            logger.info(f"최근 활동 내역 조회 성공: {query}")
            return [TextContent(type="text", text=json.dumps(customer["interactions"], indent=2, ensure_ascii=False))]
        logger.warning(f"고객을 찾을 수 없음: {query} (get_recent_interactions)")
        return [TextContent(type="text", text=f"Customer '{query}' not found.")]

    elif name == "add_meeting_note":
        cust_id = arguments["cust_id"]
        note = arguments["note"]
        date = arguments.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        customer = next((c for c in data if c["id"] == cust_id), None)
        if customer:
            new_interaction = {"date": date, "type": "Meeting", "notes": note}
            # 최신순으로 맨 앞에 추가
            customer["interactions"].insert(0, new_interaction) 
            save_data(data)
            logger.info(f"미팅 노트 추가 완료: {cust_id}, 날짜: {date}, 내용: {note}")
            return [TextContent(type="text", text=f"Note added to {customer['name']} successfully.")]
        logger.warning(f"고객 ID를 찾을 수 없음: {cust_id} (add_meeting_note)")
        return [TextContent(type="text", text=f"Customer ID '{cust_id}' not found.")]

    raise ValueError(f"Unknown tool: {name}")

# ------------------------------------------------------------------------------
# Resources (리소스) 정의
# ------------------------------------------------------------------------------

@app.list_resources()
async def list_resources() -> list[Resource]:
    """클라이언트가 읽을 수 있는 리소스 목록을 정의합니다."""
    return [
        Resource(
            uri="sales://dashboard",
            name="Sales Dashboard",
            description="Overview of high-risk customers (고위험 고객 현황 대시보드)",
            mimeType="application/json"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str | bytes:
    """클라이언트가 특정 리소스를 요청했을 때 데이터를 반환합니다."""
    logger.info(f"리소스 읽기 요청: {uri}")
    uri = str(uri) # Pydantic AnyUrl 타입을 문자열로 변환
    if uri == "sales://dashboard":
        data = load_data()
        # 리스크 점수가 High인 고객만 필터링
        high_risk = [c["name"] for c in data if c["risk_score"] == "High"]
        logger.info(f"대시보드 생성 완료. 고위험 고객 수: {len(high_risk)}명")
        return json.dumps({"high_risk_customers": high_risk, "total_customers": len(data)}, indent=2)
    logger.warning(f"알 수 없는 리소스 요청: {uri}")
    raise ValueError(f"Unknown resource: {uri}")

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
        logger.info("서버를 SSE 모드로 시작합니다. 포트: 8001")
        uvicorn.run(starlette_app, host="0.0.0.0", port=8001)
    else:
        # 기본은 STDIO 모드로 실행
        logger.info("서버를 Stdio 모드로 시작합니다")
        asyncio.run(app.run_stdio_async())
