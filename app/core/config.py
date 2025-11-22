# app/core/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str | None = None  # just to avoid validation issues if still in .env

    # Local LLM (Ollama) config
    LOCAL_LLM_URL: str = "http://localhost:11434/api/generate"
    LOCAL_LLM_MODEL: str = "deepseek-r1:1.5b"

    class Config:
        env_file = ".env"


settings = Settings()
