"""Central configuration. All settings come from environment variables / .env."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # utf-8-sig tolerates the BOM that some Windows editors add to .env files
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8-sig", extra="ignore"
    )

    app_name: str = "MeetWise AI"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./meetwise.db"
    cors_origins: str = "http://localhost:3000"

    tavily_api_key: str = ""
    # --- AI provider -------------------------------------------------------
    # LLM_PROVIDER=anthropic          -> uses ANTHROPIC_API_KEY + CLAUDE_MODEL
    # LLM_PROVIDER=openai_compatible  -> uses LLM_API_KEY + LLM_BASE_URL + LLM_MODEL
    #   (works with Google Gemini, OpenAI, Groq, OpenRouter and similar)
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_fallback_model: str = ""  # optional backup used if the main model is overloaded

    # MOCK_MODE=true runs the whole pipeline on clearly-labelled demo data
    # (no Tavily/Claude calls). Mock briefings are flagged everywhere.
    mock_mode: bool = False

    news_window_days: int = 30
    max_sources_total: int = 30

    @field_validator("llm_provider")
    @classmethod
    def _normalise_provider(cls, v: str) -> str:
        v = v.strip().lower().replace("-", "_")
        if v in {"openai", "openai_compatible", "gemini", "groq", "openrouter"}:
            return "openai_compatible"
        return "anthropic"

    @property
    def llm_missing(self) -> list[str]:
        """Names of required AI settings that are empty."""
        if self.llm_provider == "openai_compatible":
            pairs = (("LLM_API_KEY", self.llm_api_key), ("LLM_BASE_URL", self.llm_base_url), ("LLM_MODEL", self.llm_model))
        else:
            pairs = (("ANTHROPIC_API_KEY", self.anthropic_api_key),)
        return [name for name, value in pairs if not value]

    @property
    def llm_configured(self) -> bool:
        return not self.llm_missing

    @property
    def llm_model_name(self) -> str:
        return self.llm_model if self.llm_provider == "openai_compatible" else self.claude_model

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, v: str) -> str:
        # Render hands out postgres:// or postgresql:// URLs; SQLAlchemy needs a driver
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
