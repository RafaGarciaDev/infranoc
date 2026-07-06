from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INFRANOC_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://infranoc:infranoc@localhost:5432/infranoc"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "troque-em-producao"
    jwt_algorithm: str = "HS256"
    access_expire_min: int = 30
    refresh_expire_days: int = 7
    # AD (Fase 5), Prometheus (Fase 3), AI (Fase 7) entram depois


settings = Settings()
