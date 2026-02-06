import asyncio
import logging
from mcp import ClientSession
from mcp.client.sse import sse_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("supply-client")

async def run_client():
    # SSE 서버 주소 (supply_server.py가 8002 포트에서 실행 중이어야 함)
    server_url = "http://localhost:8002/sse"
    logger.info(f"서버 연결 시도: {server_url}...")

    # SSE 클라이언트 연결 컨텍스트 매니저 사용
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("세션 초기화 완료")
            
            # 1. 재고 확인 (Call Tool)
            logger.info("\n--- 1. 재고 확인: X100 ---")
            logger.info("도구 호출 요청: check_product_stock, 인자: sku_or_name='X100'")
            # 'check_product_stock' 도구 호출
            res = await session.call_tool("check_product_stock", arguments={"sku_or_name": "X100"})
            logger.info(f"재고 확인 결과:\n{res.content[0].text}")

            # 2. 대체 상품 검색 (Call Tool)
            logger.info("\n--- 2. 대체 상품 검색 (Electronics) ---")
            logger.info("도구 호출 요청: find_alternative_product, 인자: category='Electronics', min_stock=200")
            # 'find_alternative_product' 도구 호출
            res = await session.call_tool("find_alternative_product", arguments={"category": "Electronics", "min_stock": 200})
            logger.info(f"대체 상품 검색 결과:\n{res.content[0].text}")

            # 3. 발주 넣기 (Call Tool - 상태 변경)
            logger.info("\n--- 3. 발주 넣기 ---")
            logger.info("도구 호출 요청: place_restock_order, 인자: sku='WIDGET-X100', quantity=500")
            # 'place_restock_order' 도구 호출
            res = await session.call_tool("place_restock_order", arguments={"sku": "WIDGET-X100", "quantity": 500})
            logger.info(f"발주 처리 결과:\n{res.content[0].text}")

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except Exception as e:
        logger.error(f"클라이언트 실행 중 오류 발생: {e}", exc_info=True)
