from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.schemas import AgentRunRequest, ToolRunRequest
from app.services.agents import DEFAULT_SYSTEM_PROMPT, Agent, AgentResult
from app.services.llm import LLMService, get_llm
from app.tools import all_tools, execute, get_tool

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/tools")
def list_tools():
    return [
        {"name": t.name, "description": t.description, "parameters": t.parameters()}
        for t in all_tools()
    ]


@router.post("/tools/{name}")
async def run_tool(name: str, req: ToolRunRequest):
    """Run one tool directly (no LLM). Handy for debugging new tools."""
    if get_tool(name) is None:
        raise NotFoundError(f"Tool '{name}' not found")
    res = await execute(name, req.arguments)
    return res.__dict__


@router.post("/run", response_model=AgentResult)
async def run_agent(req: AgentRunRequest, llm: LLMService = Depends(get_llm)):
    tools = all_tools()
    if req.tools is not None:
        tools = [t for t in tools if t.name in set(req.tools)]
    agent = Agent(
        llm,
        tools,
        system_prompt=req.system or DEFAULT_SYSTEM_PROMPT,
        max_iterations=req.max_iterations or get_settings().agent_max_iterations,
    )
    return await agent.run(req.message, [m.model_dump() for m in req.history])
