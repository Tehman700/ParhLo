import pytest

pytest.importorskip("mcp", reason="install with: uv sync --extra mcp")


async def test_mcp_server_lists_and_calls_tools():
    from app.services.mcp.client import call_tool, connect_local_server

    async with connect_local_server() as session:
        names = {t.name for t in (await session.list_tools()).tools}
        assert {"calculator", "query_database"} <= names
        result = await call_tool(session, "calculator", {"expression": "3*(4+5)"})
        assert result["result"] == 27
