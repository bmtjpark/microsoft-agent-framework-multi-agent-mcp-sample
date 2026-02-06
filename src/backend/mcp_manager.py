import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
from typing import List, Dict, Any
import logging

logger = logging.getLogger("mcp-manager")

# MCP 서버 설정
MCP_SERVERS = {
    "mcp-hr-policy": "http://localhost:8003/sse",
    "mcp-sales-crm": "http://localhost:8001/sse",
    "mcp-supply-chain": "http://localhost:8002/sse",
    "mcp-weather": "http://localhost:8004/sse"
}

async def get_mcp_tool_definitions(mcp_names: List[str]) -> List[Dict[str, Any]]:
    """
    선택된 MCP 서버들에서 도구 목록을 가져와 OpenAI Tool 스키마로 변환합니다.
    도구 이름은 충돌 방지를 위해 'mcp_{server}_{tool_name}' 형식으로 변경됩니다.
    """
    openai_tools = []

    for mcp_name in mcp_names:
        url = MCP_SERVERS.get(mcp_name)
        if not url:
            logger.warning(f"알 수 없는 MCP 서버: {mcp_name}")
            continue
        
        try:
            # MCP 서버 연결 및 도구 조회
            async with sse_client(url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    mcp_tools_result = await session.list_tools()
                    
                    for tool in mcp_tools_result.tools:
                        # OpenAI Function Definition 생성
                        # 이름에 접두사 추가
                        unique_tool_name = f"{mcp_name}__{tool.name}"
                        
                        function_def = {
                            "type": "function",
                            "function": {
                                "name": unique_tool_name,
                                "description": tool.description or "",
                                "parameters": tool.inputSchema
                            }
                        }
                        openai_tools.append(function_def)
                        logger.info(f"도구 등록됨: {unique_tool_name}")

        except Exception as e:
            logger.error(f"MCP 서버({mcp_name}) 연결 실패: {e}")
            # 일부 실패하더라도 진행

    return openai_tools

async def execute_mcp_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    접두사가 포함된 도구 이름을 파싱하여 적절한 MCP 서버에 실행 요청을 보냅니다.
    """
    # 접두사 분리 (mcp-hr-policy__get_employee_balance)
    try:
        mcp_name, real_tool_name = tool_name.split("__", 1)
    except ValueError:
        return f"Error: Invalid tool name format {tool_name}"

    url = MCP_SERVERS.get(mcp_name)
    if not url:
        return f"Error: Unknown MCP server for {mcp_name}"

    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(real_tool_name, arguments=arguments)
                
                # 결과 텍스트 추출
                output_texts = [content.text for content in result.content if content.type == 'text']
                return "\n".join(output_texts)

    except Exception as e:
        logger.error(f"도구 실행 실패 ({tool_name}): {e}")
        return f"Error executing tool: {str(e)}"
