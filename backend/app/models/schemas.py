"""Request/response models shared by the API routes."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    system: str | None = None
    json_mode: bool = False
    temperature: float | None = None
    model: str | None = None


class ChatResponse(BaseModel):
    reply: str
    data: Any = None  # parsed JSON when json_mode=True
    model: str
    usage: dict | None = None


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = []
    tools: list[str] | None = Field(default=None, description="Restrict to these tool names (default: all)")
    system: str | None = None
    max_iterations: int | None = Field(default=None, ge=1, le=20)


class ToolRunRequest(BaseModel):
    arguments: dict[str, Any] = {}


class FileInfo(BaseModel):
    name: str
    original_name: str | None = None
    kind: str
    size: int
    processing: dict | None = None
    error: str | None = None


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)


class MLFileRequest(BaseModel):
    filename: str


class MLTrainRequest(BaseModel):
    filename: str
    target: str
    task: Literal["auto", "classification", "regression"] = "auto"
    algorithm: Literal["random_forest", "gradient_boosting", "linear"] = "random_forest"
    test_size: float = Field(default=0.2, gt=0.05, lt=0.9)
    model_name: str | None = None
    drop_columns: list[str] = []


class MLPredictRequest(BaseModel):
    model_name: str
    records: list[dict[str, Any]] = Field(min_length=1)
