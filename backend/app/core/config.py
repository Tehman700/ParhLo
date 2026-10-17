"""All configuration lives here. Values come from the repo-root .env file or environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ROOT_DIR / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NaSCon AI Starter"

    # --- LLM (any OpenAI-compatible API) ---
    llm_api_key: str = ""
    llm_base_url: str | None = None  # None = api.openai.com
    llm_model: str = "gpt-4o-mini"
    llm_vision_model: str | None = None  # falls back to llm_model
    llm_temperature: float = 0.2
    llm_timeout: float = 60.0

    # --- Embeddings: "local" (offline, scikit-learn hashing) or "api" (LLM provider) ---
    embedding_provider: str = "local"
    embedding_model: str = "text-embedding-3-small"

    # --- Feature switches ---
    enable_rag: bool = True
    enable_ml: bool = True
    enable_vision: bool = True

    # --- Agent ---
    agent_max_iterations: int = 6

    # --- Paths & server ---
    data_dir: Path = ROOT_DIR / "data"  # runtime storage (uploads, sqlite, indexes, models); created on start
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def db_path(self) -> Path:
        return self.processed_dir / "app.db"

    def ensure_dirs(self) -> None:
        for d in (self.uploads_dir, self.processed_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
