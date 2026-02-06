import asyncio
import logging
from mcp import ClientSession
from mcp.client.sse import sse_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hr-client")

async def run_client():
    # SSE 서버 주소 (hr_server.py가 8003 포트에서 실행 중이어야 함)
    server_url = "http://localhost:8003/sse"
    logger.info(f"서버 연결 시도: {server_url}...")

    # SSE 클라이언트 연결 컨텍스트 매니저 사용
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("세션 초기화 완료")
            
            # 1. 정책 문서 검색 (Call Tool)
            logger.info("\n--- 1. 사내 규정 검색: '휴가' ---")
            logger.info("도구 호출 요청: search_policy_docs, 인자: query='휴가'")
            # 'search_policy_docs' 도구 호출
            res = await session.call_tool("search_policy_docs", arguments={"query": "휴가"})
            logger.info(f"검색 결과:\n{res.content[0].text}")

            # 2. 휴가 잔여일수 확인 (Call Tool)
            logger.info("\n--- 2. 휴가 잔여일수 확인: emp_001 ---")
            logger.info("도구 호출 요청: get_employee_balance, 인자: employee_id='emp_001'")
            # 'get_employee_balance' 도구 호출
            res = await session.call_tool("get_employee_balance", arguments={"employee_id": "emp_001"})
            logger.info(f"잔여일수 조회 결과:\n{res.content[0].text}")

            # 3. 휴가 신청 (Call Tool - 상태 변경)
            logger.info("\n--- 3. 휴가 신청 요청 (3일) ---")
            logger.info("도구 호출 요청: submit_leave_request, 인자: employee_id='emp_001', type='vacation', days=3")
            # 'submit_leave_request' 도구 호출
            res = await session.call_tool("submit_leave_request", arguments={"employee_id": "emp_001", "type": "vacation", "days": 3})
            logger.info(f"신청 처리 결과:\n{res.content[0].text}")

            # 4. 신청 후 잔여일수 재확인 (상태 변경 확인)
            logger.info("\n--- 4. 신청 후 잔여일수 재확인: emp_001 ---")
            logger.info("도구 호출 요청: get_employee_balance, 인자: employee_id='emp_001'")
            res = await session.call_tool("get_employee_balance", arguments={"employee_id": "emp_001"})
            logger.info(f"변경 후 잔여일수 조회 결과:\n{res.content[0].text}")

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except Exception as e:
        logger.error(f"클라이언트 실행 중 오류 발생: {e}", exc_info=True)
