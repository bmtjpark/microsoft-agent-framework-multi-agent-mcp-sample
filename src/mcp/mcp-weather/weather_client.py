import asyncio
import sys
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

# Configure client logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("weather-client")

async def run_client():
    # To test SEE mode, ensure server is running: python src/mcp-weather/weather_server.py --sse
    # To test STDIO mode (default), just run: python src/mcp-weather/weather_client.py
    
    server_url = "http://localhost:8004/sse"
    logger.info(f"서버 연결 시도: {server_url} 중...")
    
    try:
        async with sse_client(server_url) as (read, write):
            logger.info("SSE 연결 수립됨. 세션 초기화 중...")
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                logger.info("세션 초기화 완료")

                # 1. List available tools
                logger.info("\n--- 1. 도구 목록 조회 ---")
                logger.debug("도구 목록 요청 중...")
                tools = await session.list_tools()
                logger.info(f"{len(tools.tools)}개의 도구 수신 완료")
                for tool in tools.tools:
                    logger.info(f"도구 발견: {tool.name} - {tool.description}")

                # 2. Call the weather tool
                logger.info("\n--- 2. 도구 호출: get_weather_by_location (서울) ---")
                
                params = {"location_name": "서울"}
                logger.info(f"도구 호출 요청: get_weather_by_location, 인자: {params}")
                
                result = await session.call_tool(
                    "get_weather_by_location",
                    arguments=params
                )
                logger.info("도구 실행 완료")
                
                logger.info("결과:")
                for content in result.content:
                    if content.type == "text":
                        logger.info(content.text)

                # 3. List available resources
                logger.info("\n--- 3. 리소스 목록 조회 ---")
                logger.debug("리소스 목록 요청 중...")
                resources = await session.list_resources()
                logger.info(f"{len(resources.resources)}개의 리소스 수신 완료")
                for resource in resources.resources:
                    logger.info(f"리소스 발견: {resource.name} ({resource.uri})")

                # 4. Read a static resource
                logger.info("\n--- 4. 정적 리소스 읽기: weather://status ---")
                logger.info("리소스 읽기 요청: weather://status")
                resource_content = await session.read_resource("weather://status")
                content_text = resource_content.contents[0].text
                logger.info(f"리소스 내용: {content_text}")

                # 5. Read a dynamic resource template
                target_uri = "weather://37.5665/126.9780/current"
                logger.info(f"\n--- 5. 동적 리소스 읽기: {target_uri} ---")
                logger.info(f"동적 리소스 읽기 요청: {target_uri}")
                try:
                    dynamic_content = await session.read_resource(target_uri)
                    dyn_text = dynamic_content.contents[0].text
                    logger.info(f"동적 리소스 내용: {dyn_text}")
                except Exception as e:
                    logger.error(f"동적 리소스 읽기 실패: {e}")
                    
    except Exception as e:
        logger.error("클라이언트 실행 중 오류 발생 (서버가 실행 중인지 확인하세요: python weather_server.py --sse)", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_client())
