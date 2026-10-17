"""Importing a tool module registers its @tool functions. Add new tool modules to load_tools()."""

from app.tools.registry import Tool, ToolResult, all_tools, execute, get_tool, tool

_loaded = False


def load_tools() -> None:
    global _loaded
    if _loaded:
        return
    from app.core.config import get_settings
    from app.tools import calculator, csv_tools, database  # noqa: F401

    if get_settings().enable_rag:
        from app.tools import documents  # noqa: F401
    _loaded = True


__all__ = ["Tool", "ToolResult", "all_tools", "execute", "get_tool", "tool", "load_tools"]
