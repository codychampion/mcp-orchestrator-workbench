"""
Shared utilities for MCP tool operations
"""
import asyncio
from typing import Dict, Any, List
from fastmcp import Client


async def fetch_tools_from_mcp(mcp_url: str) -> List[Dict[str, Any]]:
    """
    Fetch and format tools from MCP server.
    Consolidates duplicate tool-fetching logic.
    """
    async with Client(mcp_url) as client:
        tools = await client.list_tools()

        # Convert MCP tool format to our API format
        tools_data = []
        for tool in tools:
            tool_schema = {
                "name": tool.name,
                "description": tool.description or "No description",
                "params_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {"type": "object", "properties": {}}
            }
            tools_data.append(tool_schema)

        return tools_data


def extract_tool_result(result: Any) -> str:
    """
    Extract result content from MCP tool call response.
    Consolidates duplicate result-extraction logic from 3+ places.
    """
    if hasattr(result, 'content') and result.content:
        if isinstance(result.content, list) and len(result.content) > 0:
            output = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
        else:
            output = str(result.content)
    else:
        output = str(result)

    return output


async def call_tool_with_retry(
    mcp_url: str,
    tool_name: str,
    params: Dict[str, Any],
    timeout: float = 30.0,
    max_retries: int = 1
) -> Dict[str, Any]:
    """
    Call an MCP tool with timeout and retry logic.
    Returns: {"success": bool, "output": str, "error": str}
    """
    for attempt in range(max_retries + 1):
        try:
            async with asyncio.timeout(timeout):
                async with Client(mcp_url) as client:
                    result = await client.call_tool(tool_name, params)
                    output = extract_tool_result(result)

                    return {
                        "success": True,
                        "output": output,
                        "error": None,
                        "attempts": attempt + 1
                    }

        except asyncio.TimeoutError:
            error_msg = f"Tool '{tool_name}' timed out after {timeout}s"
            if attempt < max_retries:
                print(f"[MCP_UTILS] {error_msg}, retrying... (attempt {attempt + 2}/{max_retries + 1})")
                continue
            return {
                "success": False,
                "output": None,
                "error": error_msg,
                "attempts": attempt + 1
            }

        except Exception as e:
            error_msg = f"Tool '{tool_name}' failed: {str(e)}"
            if attempt < max_retries:
                print(f"[MCP_UTILS] {error_msg}, retrying... (attempt {attempt + 2}/{max_retries + 1})")
                continue
            return {
                "success": False,
                "output": None,
                "error": error_msg,
                "attempts": attempt + 1
            }

    # Should never reach here
    return {
        "success": False,
        "output": None,
        "error": "Unknown error",
        "attempts": max_retries + 1
    }
