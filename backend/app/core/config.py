from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Configuration
    PROJECT_NAME: str = "AI Meeting Translator"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Active Providers Selection
    STORAGE_PROVIDER: Literal["r2", "local"] = Field(default="r2")
    TRANSLATION_PROVIDER: Literal["deepl", "google", "llm"] = Field(default="deepl")
    STT_PROVIDER: Literal["faster_whisper", "whisper_live"] = Field(default="faster_whisper")
    SUMMARY_PROVIDER: Literal["openrouter", "openai", "gemini"] = Field(default="openrouter")

    # Supabase / PostgreSQL Database
    DATABASE_URL: str = Field(default="postgresql://postgres:postgres@localhost:5432/postgres")
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")

    # Storage Settings (Cloudflare R2 / S3 Compatible)
    R2_BUCKET_NAME: str = Field(default="meeting-audio-chunks")
    R2_ACCOUNT_ID: str = Field(default="")
    R2_ACCESS_KEY_ID: str = Field(default="")
    R2_SECRET_ACCESS_KEY: str = Field(default="")
    R2_ENDPOINT_URL: str = Field(default="")

    # DeepL Translation API
    DEEPL_API_KEY: str = Field(default="")

    # OpenRouter / LLM Summary Settings
    OPENROUTER_API_KEY: str = Field(default="")
    OPENROUTER_MODEL: str = Field(default="deepseek/deepseek-chat")

    # GPU Worker Configuration
    MODAL_WORKER_URL: str = Field(default="")


settings = Settings()
