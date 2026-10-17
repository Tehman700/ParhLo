"""MCP server exposing every registered @tool (calculator, database, CSV, documents...).

Requires the optional extra:  uv sync --extra mcp      (written for mcp 2.x: FastMCP is now MCPServer)
Run (stdio, for Claude Desktop / MCP clients):  uv run python -m app.services.mcp.server
Run over HTTP at http://127.0.0.1:8001/mcp:     uv run python -m app.services.mcp.server --http --port 8001
"""

import argparse

from mcp.server.mcpserver import MCPServer

from app.core.db import init_db
from app.tools import all_tools, load_tools


def build_server(name: str = "parhlo-tools") -> MCPServer:
    load_tools()
    init_db()
    server = MCPServer(name, log_level="WARNING")
    for t in all_tools():
        server.add_tool(t.func, name=t.name, description=t.description)

    # Add MCP-only tools here with @server.tool() if needed.
    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Serve streamable HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    server = build_server()
    if args.http:
        server.run(transport="streamable-http", port=args.port)
    else:
        server.run()


if __name__ == "__main__":
    main()
