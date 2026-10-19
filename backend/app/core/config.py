"""All configuration lives here. Values come from the repo-root .env file or environment variables."""

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # .env.local is written by `vercel env pull` (DATABASE_URL, VERCEL_OIDC_TOKEN, ...)
        env_file=(ROOT_DIR / ".env", ROOT_DIR / ".env.local", ROOT_DIR / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ParhLo"

    # --- LLM (any OpenAI-compatible API; defaults to Vercel AI Gateway) ---
    llm_api_key: str = ""
    ai_gateway_api_key: str = ""
    vercel_oidc_token: str = ""
    llm_base_url: str | None = "https://ai-gateway.vercel.sh/v1"
    llm_model: str = "openai/gpt-5-mini"  # editor / reasoning
    llm_fast_model: str = "openai/gpt-5-nano"  # per-article summaries, cheap and fast
    llm_vision_model: str | None = None  # falls back to llm_model
    llm_temperature: float | None = None  # None = provider default (gpt-5 models reject custom values)
    llm_timeout: float = 90.0

    # --- Embeddings: "api" (gateway) or "local" (offline, scikit-learn hashing) ---
    embedding_provider: str = "api"
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dim: int = 1536

    # --- Jev (TypeSafe System One): fast typed decisions — topics, junk, importance, summary checks ---
    typesafe_api_key: str = ""
    jev_model: str = "jev-latest"
    jev_enabled: bool = True

    # --- SWS (Smart Web Search): worldwide news every 15 minutes (GDELT, Google News editions) + Tavily ---
    sws_enabled: bool = True
    tavily_api_key: str = ""  # instant web search (1,000 free credits a month)

    # --- Database (Neon Postgres + pgvector) ---
    database_url: str = ""

    cron_secret: str = ""  # Vercel Cron sends it as a Bearer token

    # --- Auth (own: email OTP via SES + Google OAuth; signed session cookie) ---
    session_secret: str = ""  # signs session JWTs; set in Vercel env
    google_client_id: str = ""
    google_client_secret: str = ""
    n8n_webhook_url: str = ""  # n8n workflow that debounces interest changes and asks us to reprint
    public_url: str = "http://localhost:3000"  # where the browser sees the app (OAuth redirect base)
    allow_demo_users: bool = True  # X-Demo-User header for seeded personas (two-persona demo)

    # --- AWS (S3 media, Polly audio, SES email) ---
    # Not "aws_region": Vercel injects AWS_REGION (its own function region) into the runtime.
    parhlo_aws_region: str = "ap-south-1"
    # Vercel reserves AWS_* names, so the app's IAM user (parhlo-vercel) uses its own prefix.
    parhlo_aws_access_key_id: str = ""
    parhlo_aws_secret_access_key: str = ""
    # Email: Gmail SMTP (any recipient) first, SES as fallback.
    gmail_user: str = ""
    gmail_app_password: str = ""
    s3_bucket: str = "parhlo-media-109257212304"
    email_from: str = "tehmanhassan@gmail.com"

    # --- Starter modules (off for ParhLo; flip on if needed) ---
    enable_starter: bool = False  # chat/agent/files routes + tools (imports pandas/sklearn)
    enable_rag: bool = False
    enable_ml: bool = False
    enable_vision: bool = False

    # --- Agent ---
    agent_max_iterations: int = 6

    # --- Paths & server ---
    # Runtime scratch storage. Vercel's filesystem is read-only except /tmp.
    data_dir: Path = Path("/tmp/parhlo-data") if os.environ.get("VERCEL") else ROOT_DIR / "data"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def llm_key(self) -> str:
        """Explicit key > AI Gateway key > Vercel OIDC token (local dev via `vercel env pull`)."""
        return self.llm_api_key or self.ai_gateway_api_key or self.vercel_oidc_token

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_key)

    @property
    def uses_openai_direct(self) -> bool:
        """An OpenAI key (sk-...) talks to api.openai.com directly instead of the gateway."""
        return self.llm_api_key.startswith("sk-")

    @property
    def effective_base_url(self) -> str | None:
        return None if self.uses_openai_direct else (self.llm_base_url or None)

    def model_name(self, name: str) -> str:
        """Gateway ids are 'provider/model'; OpenAI direct wants just 'model'."""
        return name.split("/", 1)[1] if self.uses_openai_direct and "/" in name else name

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
