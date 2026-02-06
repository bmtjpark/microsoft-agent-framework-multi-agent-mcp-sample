import asyncio
import logging
import httpx
from typing import Any, Sequence

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource,
    ResourceTemplate,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("weather-server")

app = Server("weather-server")

# Open-Meteo API Base URL
API_BASE_URL = "https://api.open-meteo.com/v1"
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1"

@app.list_tools()
async def list_tools() -> list[Tool]:
    logger.debug("제공 가능한 도구 목록 조회 요청")
    tools = [
        Tool(
            name="get_weather_forecast",
            description="위도와 경도를 사용하여 특정 지역의 날씨 예보를 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "지역의 위도 (예: 37.5665)",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "지역의 경도 (예: 126.9780)",
                    },
                },
                "required": ["latitude", "longitude"],
            },
        ),
        Tool(
            name="get_weather_by_location",
            description="지명(도시 이름, 구 등)을 입력받아 해당 지역의 날씨를 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": "지역 이름 (예: 서울, 서초구, New York)",
                    },
                },
                "required": ["location_name"],
            },
        )
    ]
    logger.debug(f"도구 목록 반환 완료: {len(tools)}개")
    return tools

@app.call_tool()
async def call_tool(
    name: str, arguments: Any
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    logger.info(f"도구 실행 요청: {name}, 인자: {arguments}")
    
    if name == "get_weather_forecast":
        lat = arguments.get("latitude")
        lon = arguments.get("longitude")
        
        if lat is None or lon is None:
            logger.error("필수 인자 누락: 위도(latitude) 또는 경도(longitude)")
            raise ValueError("Latitude and Longitude are required.")

        logger.debug(f"Open-Meteo API 날씨 조회 요청 (위도={lat}, 경도={lon})")
        async with httpx.AsyncClient() as client:
            try:
                # Fetch forecast data (temperature, windspeed)
                response = await client.get(
                    f"{API_BASE_URL}/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current_weather": "true",
                        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m"
                    }
                )
                logger.debug(f"API 응답 상태 코드: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                logger.debug(f"API 응답 데이터 수신 완료: {len(str(data))} bytes")
                
                current = data.get("current_weather", {})
                
                weather_summary = (
                    f"Location: {lat}, {lon}\n"
                    f"Temperature: {current.get('temperature')}°C\n"
                    f"Wind Speed: {current.get('windspeed')} km/h\n"
                    f"Time: {current.get('time')}"
                )
                
                logger.info(f"날씨 정보 조회 성공: {lat}, {lon}")
                return [TextContent(type="text", text=weather_summary)]
            
            except httpx.HTTPError as e:
                logger.error(f"날씨 API 호출 오류: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Failed to fetch weather data: {str(e)}")]

    elif name == "get_weather_by_location":
        loc_name = arguments.get("location_name")
        if not loc_name:
            logger.error("필수 인자 누락: 지역 이름(location_name)")
            raise ValueError("Location name is required.")

        logger.debug(f"지오코딩(Geocoding) 요청: {loc_name}")
        async with httpx.AsyncClient() as client:
            try:
                # 1. Geocoding to get lat/lon
                geo_res = await client.get(
                    f"{GEOCODING_API_URL}/search",
                    params={"name": loc_name, "count": 1, "language": "ko", "format": "json"}
                )
                geo_res.raise_for_status()
                geo_data = geo_res.json()
                
                if not geo_data.get("results"):
                    logger.warning(f"지명 검색 실패: {loc_name}")
                    return [TextContent(type="text", text=f"'{loc_name}'을(를) 찾을 수 없습니다.")]
                
                location = geo_data["results"][0]
                lat = location["latitude"]
                lon = location["longitude"]
                resolved_name = f"{location['name']}, {location.get('country', '')}"
                
                logger.info(f"지명 검색 성공: {resolved_name} (위도: {lat}, 경도: {lon})")

                # 2. Fetch weather
                logger.debug(f"날씨 API 요청 전송: {resolved_name}")
                response = await client.get(
                    f"{API_BASE_URL}/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current_weather": "true",
                        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                current = data.get("current_weather", {})
                
                weather_summary = (
                    f"지역: {resolved_name} ({lat}, {lon})\n"
                    f"기온: {current.get('temperature')}°C\n"
                    f"풍속: {current.get('windspeed')} km/h\n"
                    f"시간: {current.get('time')}"
                )
                
                logger.info(f"날씨 정보 조회 성공: {resolved_name}")
                return [TextContent(type="text", text=weather_summary)]

            except httpx.HTTPError as e:
                logger.error(f"API 처리 중 오류 발생: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Failed to fetch data: {str(e)}")]

    logger.warning(f"알 수 없는 도구 실행 요청: {name}")
    raise ValueError(f"Unknown tool: {name}")

@app.list_resources()
async def list_resources() -> list[Resource]:
    logger.debug("리소스 목록 조회 요청")
    return [
        Resource(
            uri="weather://status",
            name="API Status",
            description="Current status of the Weather API Connection",
            mimeType="text/plain",
        )
    ]

@app.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    logger.debug("리소스 템플릿 목록 조회 요청")
    return [
        ResourceTemplate(
            uriTemplate="weather://{latitude}/{longitude}/current",
            name="Current Weather Location",
            description="Get current weather for any location via resource URI",
            mimeType="application/json"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str | bytes:
    logger.info(f"리소스 읽기 요청: {uri}")
    
    # Ensure uri is string (mcp might pass AnyUrl object)
    uri_str = str(uri)
    
    if uri_str == "weather://status":
        logger.debug("정적 리소스 상태(Status) 반환")
        return "Online (Open-Meteo Public API)"
    
    # Simple parsing for template: weather://lat/long/current
    if uri_str.startswith("weather://") and uri_str.endswith("/current"):
        try:
            parts = uri_str.replace("weather://", "").split("/")
            if len(parts) >= 2:
                lat, lon = parts[0], parts[1]
                logger.debug(f"동적 리소스 URI 파싱됨 - 위도: {lat}, 경도: {lon}")
                
                async with httpx.AsyncClient() as client:
                     logger.debug(f"리소스용 날씨 API 요청 (위도: {lat}, 경도: {lon})")
                     response = await client.get(
                        f"{API_BASE_URL}/forecast",
                        params={
                            "latitude": lat,
                            "longitude": lon,
                            "current_weather": "true"
                        }
                    )
                     data = response.json()
                     logger.debug(f"API 응답 데이터 수신 완료: {len(str(data))} bytes")
                     return str(data.get("current_weather", {}))
        except Exception as e:
            logger.error(f"리소스 읽기 중 오류 발생: {e}", exc_info=True)
            raise ValueError(f"Failed to fetch resource: {e}")

    logger.warning(f"알 수 없는 리소스 URI 요청: {uri}")
    raise ValueError(f"Unknown resource: {uri}")

async def handle_sse(request):
    logger.info("새로운 SSE 연결 시도 감지")
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        logger.info("SSE 연결 수립됨. 앱 세션 실행 시작")
        await app.run(
            streams[0], streams[1], app.create_initialization_options()
        )
    logger.info("SSE 연결 종료됨")
    
    class NoOpResponse:
        async def __call__(self, scope, receive, send):
            pass
    return NoOpResponse()

async def handle_messages(request):
    logger.info("POST 메시지 수신됨")
    await sse.handle_post_message(request.scope, request.receive, request._send)
    class NoOpResponse:
        async def __call__(self, scope, receive, send):
            pass
    return NoOpResponse()

sse = SseServerTransport("/messages")

starlette_app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ],
)

async def main():
    import sys
    # Check command line arguments for mode
    mode = "stdio"
    if len(sys.argv) > 1:
        if sys.argv[1] == "--sse":
            mode = "sse"
    
    if mode == "stdio":
        logger.info("서버를 Stdio 모드로 시작합니다")
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="weather-server",
                    server_version="0.1.0",
                    capabilities=app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    elif mode == "sse":
        logger.info("서버를 SSE 모드로 시작합니다. 포트: 8004")
        import uvicorn
        config = uvicorn.Config(starlette_app, host="0.0.0.0", port=8004, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
