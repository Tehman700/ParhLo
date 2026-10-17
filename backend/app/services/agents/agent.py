"""A plain tool-calling agent loop.

user message -> LLM (with tool schemas) -> run requested tools -> feed results back -> repeat
until the LLM answers without tool calls, or max_iterations is hit.
Every tool execution is recorded as a step so the frontend can show it.
"""

import json
import time
from typing import Any

from pydantic import BaseModel

from app.services.llm import LLMService
from app.tools import Tool, execute

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to tools. "
    "Use tools when they help answer accurately; do not guess values a tool can compute or look up. "
    "When you have enough information, answer clearly and concisely."
)
MAX_TOOL_OUTPUT_CHARS = 8000


class AgentStep(BaseModel):
    iteration: int
    tool: str
    arguments: dict[str, Any]
    result: Any = None
    error: str | None = None
    duration_ms: float


class AgentResult(BaseModel):
    answer: str
    steps: list[AgentStep]
    iterations: int
    duration_ms: float
    model: str = ""
    stopped_reason: str = "completed"  # "completed" | "max_iterations"


class Agent:
    def __init__(
        self,
        llm: LLMService,
        tools: list[Tool],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_iterations: int = 6,
    ):
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    async def run(self, user_message: str, history: list[dict] | None = None) -> AgentResult:
        start = time.perf_counter()
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        messages += history or []
        messages.append({"role": "user", "content": user_message})
        schemas = [t.openai_schema() for t in self.tools] or None
        allowed = {t.name for t in self.tools}

        steps: list[AgentStep] = []
        model = ""
        for iteration in range(1, self.max_iterations + 1):
            reply = await self.llm.chat(messages, tools=schemas)
            model = reply.model or model
            if not reply.tool_calls:
                return self._result(reply.content or "", steps, iteration, start, model)

            messages.append({
                "role": "assistant",
                "content": reply.content,
                "tool_calls": [
                    {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                    for c in reply.tool_calls
                ],
            })
            for call in reply.tool_calls:
                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if call.name in allowed:
                    res = await execute(call.name, args)
                    result, error, duration = res.result, res.error, res.duration_ms
                else:
                    result, error, duration = None, f"Tool '{call.name}' is not available", 0.0
                steps.append(AgentStep(
                    iteration=iteration, tool=call.name, arguments=args,
                    result=result, error=error, duration_ms=duration,
                ))
                payload = {"error": error} if error else {"result": result}
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(payload, default=str)[:MAX_TOOL_OUTPUT_CHARS],
                })

        # Out of iterations: ask for a final answer with no more tools.
        messages.append({"role": "user", "content": "Stop using tools and give your best final answer now."})
        reply = await self.llm.chat(messages)
        result = self._result(reply.content or "", steps, self.max_iterations, start, reply.model or model)
        result.stopped_reason = "max_iterations"
        return result

    @staticmethod
    def _result(answer: str, steps: list[AgentStep], iterations: int, start: float, model: str) -> AgentResult:
        return AgentResult(
            answer=answer,
            steps=steps,
            iterations=iterations,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
            model=model,
        )
