"""MCP client: connect to any MCP server, discover its tools, and call them.

Demo (spawns our own server over stdio):
    uv run python -m app.services.mcp.client

To let the agent use a remote MCP server's tools: list_tools(), then register each one in
app.tools.registry as a Tool whose func awaits call_tool(session, name, args).
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BACKEND_DIR = Path(__file__).resolve().parents[3]


@asynccontextmanager
async def connect_stdio(command: str, args: list[str], cwd: Path | None = None):
    params = StdioServerParameters(
        command=command, args=args, cwd=str(cwd) if cwd else None, env=dict(os.environ)
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@asynccontextmanager
async def connect_local_server():
    """Spawn this project's MCP server as a subprocess."""
    async with connect_stdio(sys.executable, ["-m", "app.services.mcp.server"], cwd=BACKEND_DIR) as s:
        yield s


async def call_tool(session: ClientSession, name: str, arguments: dict) -> object:
    result = await session.call_tool(name, arguments)
    if getattr(result, "is_error", False):
        raise RuntimeError(f"MCP tool '{name}' failed: {result.content}")
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content
    texts = [c.text for c in getattr(result, "content", []) if getattr(c, "type", "") == "text"]
    joined = "\n".join(texts)
    try:
        return json.loads(joined)
    except json.JSONDecodeError:
        return joined


async def demo() -> None:
    async with connect_local_server() as session:
        tools = await session.list_tools()
        print("Tools:", [t.name for t in tools.tools])
        print("calculator ->", await call_tool(session, "calculator", {"expression": "2 ** 10 + sqrt(81)"}))
        print("list_tables ->", await call_tool(session, "list_tables", {}))


if __name__ == "__main__":
    asyncio.run(demo())
