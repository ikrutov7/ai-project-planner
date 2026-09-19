"""Application settings loaded from environment / .env."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_SQLITE = f"sqlite:///{BACKEND_ROOT / 'data' / 'planner.db'}"


class Settings(BaseSettings):
    """Uses PLANNER_* env vars so a global DATABASE_URL cannot hijack the app."""

    model_config = SettingsConfigDict(
        env_prefix="PLANNER_",
        env_file=(".env", str(REPO_ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Project Planner"
    debug: bool = False
    database_url: str = DEFAULT_SQLITE
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    serve_frontend: bool = True

    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_max_iterations: int = 8
    agent_demo_mode: bool = True

    @model_validator(mode="after")
    def _merge_unprefixed_llm(self) -> Settings:
        if not self.llm_api_key.strip():
            self.llm_api_key = (
                os.getenv("LLM_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or ""
            )
        if os.getenv("LLM_MODEL"):
            self.llm_model = os.getenv("LLM_MODEL", self.llm_model)
        if os.getenv("LLM_BASE_URL"):
            self.llm_base_url = os.getenv("LLM_BASE_URL", self.llm_base_url)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
