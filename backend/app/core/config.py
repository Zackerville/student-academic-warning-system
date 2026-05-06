from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Student Warning System"
    APP_ENV: str = "development"
    DEBUG: bool = True

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "warning_ai_db"
    POSTGRES_USER: str = "warning_user"
    POSTGRES_PASSWORD: str = "warning_password"
    DATABASE_URL: str = "postgresql+asyncpg://warning_user:warning_password@postgres:5432/warning_ai_db"

    PGADMIN_DEFAULT_EMAIL: str = "admin@example.com"
    PGADMIN_DEFAULT_PASSWORD: str = "admin123"

    SECRET_KEY: str = "change_this_secret_key_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002,http://localhost:8000"

    CHAT_PROVIDER: str = "extractive"
    EMBEDDING_PROVIDER: str = "hash"
    VECTOR_STORE: str = "pgvector"
    RAG_TOP_K: int = 5
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 120
    RAG_ENABLE_OCR: bool = True
    RAG_OCR_LANG: str = "vie+eng"
    RAG_OCR_DPI: int = 220
    RAG_OCR_MAX_PAGES: int = 120

    GEMINI_API_KEY: str = ""
    GEMINI_CHAT_MODEL: str = "models/gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"

    HUGGINGFACE_API_TOKEN: str = ""
    HF_CHAT_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    HF_EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

    LOCAL_LLM_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_LLM_MODEL: str = "qwen2.5:7b"

    # ─── Email / SMTP (M6) ────────────────────────────────────
    EMAIL_ENABLED: bool = True
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@hcmut.edu.vn"
    EMAIL_FROM_NAME: str = "Hệ thống Cảnh báo Học vụ HCMUT"
    APP_BASE_URL: str = "http://localhost:3000"

    # ─── Warning thresholds (HCMUT) ───────────────────────────
    AI_EARLY_WARNING_THRESHOLD: float = 0.6

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
