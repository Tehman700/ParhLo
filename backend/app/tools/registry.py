"""Tool registry. Decorate a plain function with @tool and the agent (and MCP server) can use it.

    @tool(description="Add two numbers")
    def add(a: Annotated[float, Field(description="first")], b: float = 0) -> float:
        return a + b

The JSON schema the LLM sees is built from the type hints, so keep them accurate.
"""

import asyncio
import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, create_model


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    args_model: type[BaseModel]

    def parameters(self) -> dict:
        schema = self.args_model.model_json_schema()
        schema.pop("title", None)
        for prop in schema.get("properties", {}).values():
            prop.pop("title", None)
        return schema

    def openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters(),
            },
        }

    async def run(self, arguments: dict) -> Any:
        args = self.args_model.model_validate(arguments).model_dump()
        if inspect.iscoroutinefunction(self.func):
            return await self.func(**args)
        return await asyncio.to_thread(self.func, **args)


@dataclass
class ToolResult:
    name: str
    arguments: dict
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


_REGISTRY: dict[str, Tool] = {}


def tool(name: str | None = None, description: str | None = None):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or func.__name__
        fields: dict[str, Any] = {}
        for pname, param in inspect.signature(func).parameters.items():
            annotation = param.annotation if param.annotation is not inspect.Parameter.empty else Any
            default = param.default if param.default is not inspect.Parameter.empty else ...
            fields[pname] = (annotation, default)
        args_model = create_model(f"{tool_name}_args", **fields)
        desc = description or inspect.getdoc(func) or tool_name
        _REGISTRY[tool_name] = Tool(tool_name, desc, func, args_model)
        return func

    return decorator


def get_tool(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def all_tools() -> list[Tool]:
    return list(_REGISTRY.values())


async def execute(name: str, arguments: dict) -> ToolResult:
    """Run a tool by name, capturing errors and timing instead of raising."""
    start = time.perf_counter()
    result = ToolResult(name=name, arguments=arguments)
    t = get_tool(name)
    if t is None:
        result.error = f"Unknown tool '{name}'"
    else:
        try:
            result.result = await t.run(arguments)
        except Exception as e:  # tools must never crash the agent loop
            result.error = f"{type(e).__name__}: {e}"
    result.duration_ms = round((time.perf_counter() - start) * 1000, 2)
    return result
