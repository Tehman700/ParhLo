"""Single entry point for every LLM call in the backend.

Works with any OpenAI-compatible API (OpenAI, Vercel AI Gateway, Groq, OpenRouter,
Gemini's OpenAI endpoint, Ollama, LM Studio...). Swap providers via .env only.
"""

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.core.errors import NotConfiguredError, UpstreamError

Message = dict[str, Any]  # OpenAI chat message format


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON string from the model


@dataclass
class LLMReply:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    usage: dict[str, int] | None = None


class LLMService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if not self.settings.llm_configured:
            raise NotConfiguredError(
                "LLM is not configured. Set LLM_API_KEY (and LLM_BASE_URL / LLM_MODEL) in .env"
            )
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.settings.llm_key,
                base_url=self.settings.llm_base_url or None,
                timeout=self.settings.llm_timeout,
            )
        return self._client

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> LLMReply:
        kwargs: dict[str, Any] = {"model": model or self.settings.llm_model, "messages": messages}
        temp = self.settings.llm_temperature if temperature is None else temperature
        if temp is not None:
            kwargs["temperature"] = temp
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if max_tokens:
            kwargs["max_completion_tokens"] = max_tokens

        try:
            resp = await self.client.chat.completions.create(**kwargs)
        except openai.BadRequestError as e:
            # Some providers reject response_format; retry once without it.
            if json_mode and "response_format" in str(e):
                kwargs.pop("response_format")
                resp = await self._create(kwargs)
            else:
                raise UpstreamError(f"LLM rejected the request: {e}") from e
        except openai.APIError as e:
            raise UpstreamError(f"LLM request failed: {e}") from e

        msg = resp.choices[0].message
        calls = [
            ToolCall(id=c.id, name=c.function.name, arguments=c.function.arguments or "{}")
            for c in (msg.tool_calls or [])
        ]
        usage = resp.usage.model_dump() if resp.usage else None
        return LLMReply(content=msg.content, tool_calls=calls, model=resp.model, usage=usage)

    async def _create(self, kwargs: dict):
        try:
            return await self.client.chat.completions.create(**kwargs)
        except openai.APIError as e:
            raise UpstreamError(f"LLM request failed: {e}") from e

    async def complete(self, prompt: str, system: str | None = None, **kw) -> str:
        """One-shot text completion."""
        messages: list[Message] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return (await self.chat(messages, **kw)).content or ""

    async def json(
        self, messages: list[Message], schema: type[BaseModel] | None = None, **kw
    ) -> Any:
        """Ask for JSON. With a Pydantic schema, the result is validated and returned as a model."""
        messages = list(messages)
        instruction = "Respond with a single valid JSON object only."
        if schema:
            instruction += f" It must match this JSON schema:\n{json.dumps(schema.model_json_schema())}"
        messages.insert(0, {"role": "system", "content": instruction})

        reply = await self.chat(messages, json_mode=True, **kw)
        data = parse_json(reply.content or "")
        if schema:
            try:
                return schema.model_validate(data)
            except ValidationError as e:
                raise UpstreamError(f"LLM JSON did not match schema: {e}") from e
        return data

    async def stream(self, messages: list[Message], *, model: str | None = None) -> AsyncIterator[str]:
        """Yield text deltas as they arrive."""
        try:
            extra = {} if self.settings.llm_temperature is None else {"temperature": self.settings.llm_temperature}
            stream = await self.client.chat.completions.create(
                model=model or self.settings.llm_model, messages=messages, stream=True, **extra
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.APIError as e:
            raise UpstreamError(f"LLM stream failed: {e}") from e

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        try:
            resp = await self.client.embeddings.create(
                model=model or self.settings.embedding_model, input=texts
            )
        except openai.APIError as e:
            raise UpstreamError(f"Embedding request failed: {e}") from e
        return [d.embedding for d in resp.data]


def parse_json(text: str) -> Any:
    """Parse JSON from model output, tolerating ```json fences and surrounding prose."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    raise UpstreamError(f"LLM did not return valid JSON: {text[:200]}")


_llm: LLMService | None = None


def get_llm() -> LLMService:
    """FastAPI dependency. Override in tests with app.dependency_overrides[get_llm]."""
    global _llm
    if _llm is None:
        _llm = LLMService()
    return _llm
