"""MCP Server 入口模块。

使用方式：
    python -m easytransfer.mcp_server
"""

import asyncio

from easytransfer.mcp.server import run_server


def main() -> None:
    """MCP Server 入口。"""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
