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
logger = logging.getLogger("supply-server")

# MCP 서버 인스턴스 생성, 이름은 'supply-chain'
app = Server("supply-chain")

# Mock 데이터 경로 설정 (inventory.json 파일을 사용)
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "inventory.json")

def load_data():
    """inventory.json 파일에서 데이터를 읽어옵니다."""
    logger.info(f"재고 데이터 로딩 중: {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    """데이터를 inventory.json 파일에 저장합니다."""
    logger.info(f"재고 데이터 저장 중: {DATA_PATH}")
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ------------------------------------------------------------------------------
# Tools (도구) 정의
# ------------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    """클라이언트에게 제공할 도구(함수) 목록을 정의합니다."""
    logger.info("제공 가능한 도구 목록 조회 요청")
    return [
        Tool(
            name="check_product_stock",
            description="Check stock level and location for a product. (제품의 재고 수량과 위치를 확인합니다)",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku_or_name": {"type": "string", "description": "SKU or Product Name (SKU 또는 제품명)"}
                },
                "required": ["sku_or_name"]
            }
        ),
        Tool(
            name="find_alternative_product",
            description="Find products in the same category with sufficient stock. (같은 카테고리의 대체 상품 중 재고가 충분한 것을 찾습니다)",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Product Category (카테고리, 예: Electronics)"},
                    "min_stock": {"type": "number", "description": "Minimum required stock (필요한 최소 재고)"}
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="place_restock_order",
            description="Place an order for more stock. (재고 보충 발주를 넣습니다 - 상태 변경)",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "description": "Target SKU (대상 제품 SKU)"},
                    "quantity": {"type": "number", "description": "Amount to order (발주 수량)"}
                },
                "required": ["sku", "quantity"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """클라이언트가 도구 실행을 요청했을 때 호출됩니다."""
    logger.info(f"도구 실행 요청: {name}, 인자: {arguments}")
    data = load_data()
    
    if name == "check_product_stock":
        query = arguments["sku_or_name"].lower()
        # SKU 또는 이름에서 검색어 매칭
        product = next((p for p in data if query in p["sku"].lower() or query in p["name"].lower()), None)
        if product:
            logger.info(f"제품 재고 확인 성공: {query}")
            return [TextContent(type="text", text=json.dumps(product, indent=2))]
        logger.warning(f"제품을 찾을 수 없음: {query} (check_product_stock)")
        return [TextContent(type="text", text=f"Product '{query}' not found.")]

    elif name == "find_alternative_product":
        cat = arguments["category"]
        min_qty = arguments.get("min_stock", 0)
        # 같은 카테고리이면서 재고가 min_stock 이상인 제품 필터링
        alts = [p for p in data if p["category"].lower() == cat.lower() and p["stock"] >= min_qty]
        logger.info(f"대체 상품 검색 완료: 카테고리 '{cat}', 결과 {len(alts)}건")
        return [TextContent(type="text", text=json.dumps(alts, indent=2))]

    elif name == "place_restock_order":
        sku = arguments["sku"]
        qty = arguments["quantity"]
        product = next((p for p in data if p["sku"] == sku), None)
        if product:
            # 상태 변경: 재고 수량 증가
            product["stock"] += qty
            save_data(data)
            logger.info(f"재고 발주 처리됨: {sku}, 수량: {qty}, 현재 재고: {product['stock']}")
            return [TextContent(type="text", text=f"Order placed. New stock for {sku}: {product['stock']}")]
        logger.warning(f"발주 대상 SKU 없음: {sku} (place_restock_order)")
        return [TextContent(type="text", text=f"SKU {sku} not found.")]

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
        logger.info("서버를 SSE 모드로 시작합니다. 포트: 8002")
        uvicorn.run(starlette_app, host="0.0.0.0", port=8002)
    else:
        # 기본은 STDIO 모드로 실행
        logger.info("서버를 Stdio 모드로 시작합니다")
        asyncio.run(app.run_stdio_async())
