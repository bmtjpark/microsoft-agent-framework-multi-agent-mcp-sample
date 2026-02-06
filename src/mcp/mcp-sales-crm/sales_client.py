import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sales-client")

async def run_client():
    # SSE 서버 주소 (sales_server.py가 8001 포트에서 실행 중이어야 함)
    server_url = "http://localhost:8001/sse"
    logger.info(f"서버 연결 시도: {server_url}...")

    # SSE 클라이언트 연결 컨텍스트 매니저 사용
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("세션 초기화 완료")
            
            # 1. 고객 프로필 조회 (Call Tool)
            logger.info("\n--- 1. 고객 프로필 조회: 태산 ---")
            logger.info("도구 호출 요청: get_customer_profile, 인자: cust_name_or_id='태산'")
            # 'get_customer_profile' 도구 호출
            result = await session.call_tool("get_customer_profile", arguments={"cust_name_or_id": "태산"})
            # 결과 텍스트 출력
            logger.info(f"조회 결과:\n{result.content[0].text}")

            # 2. 미팅 노트 추가 (Call Tool)
            logger.info("\n--- 2. 미팅 노트 추가 ---")
            note_content = "CEO가 엔터프라이즈 플러스 요금제 업그레이드에 관심을 보임."
            logger.info(f"도구 호출 요청: add_meeting_note, 인자: cust_id='cust_001', note='{note_content}'")
            add_res = await session.call_tool("add_meeting_note", arguments={
                "cust_id": "cust_001",
                "note": note_content
            })
            logger.info(f"추가 결과:\n{add_res.content[0].text}")

            # 3. 리소스 읽기 (Read Resource)
            logger.info("\n--- 3. 영업 대시보드 리소스 조회 ---")
            logger.info("리소스 읽기 요청: uri='sales://dashboard'")
            # 'sales://dashboard' URI를 가진 리소스를 직접 읽어옴
            res = await session.read_resource("sales://dashboard")
            logger.info(f"리소스 내용:\n{res.contents[0].text}")

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except Exception as e:
        logger.error(f"클라이언트 실행 중 오류 발생: {e}", exc_info=True)
