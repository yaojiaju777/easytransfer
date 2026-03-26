"""EasyTransfer MCP Server 实现。

这是 Agent 调用我们技能包的入口。MCP Server 注册 6 个工具，
Agent 通过 MCP 协议调用这些工具来完成电脑迁移。

启动方式：
    python -m easytransfer.mcp_server
"""

from __future__ import annotations

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from easytransfer.core.config import APP_NAME, VERSION
from easytransfer.core.logging import get_logger
from easytransfer.mcp.tools import TOOL_DEFINITIONS, handle_tool_call

logger = get_logger(__name__)


def create_server() -> Server:
    """创建并配置 MCP Server 实例。"""
    server = Server(f"{APP_NAME}-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """返回所有可用工具列表。"""
        return [
            Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                inputSchema=tool_def["input_schema"],
            )
            for tool_def in TOOL_DEFINITIONS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """处理工具调用请求。"""
        logger.info("Agent 调用工具: %s", name)
        result = await handle_tool_call(name, arguments)
        return [TextContent(type="text", text=result)]

    return server


async def run_server() -> None:
    """启动 MCP Server（stdio 模式）。"""
    logger.info("%s MCP Server v%s 启动中...", APP_NAME, VERSION)
    server = create_server()

    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP Server 已就绪，等待 Agent 连接...")
        await server.run(read_stream, write_stream, server.create_initialization_options())
