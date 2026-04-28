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

    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001,http://localhost:8000"

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