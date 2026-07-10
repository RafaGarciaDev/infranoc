from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INFRANOC_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://infranoc:infranoc@localhost:5432/infranoc"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "troque-em-producao"
    jwt_algorithm: str = "HS256"
    access_expire_min: int = 30
    refresh_expire_days: int = 7

    # Basic auth do webhook do AlertManager (Fase 3 - Bloco 4)
    alertmanager_webhook_user: str = "alertmanager"
    alertmanager_webhook_pass: str = "changeme"

    # AD (Fase 5)
    ad_server: str = "192.168.56.10"
    ad_port: int = 389
    ad_use_ssl: bool = False
    ad_bind_user: str = "svc_infranoc@infranoc.lab"
    ad_bind_password: str = ""            # env INFRANOC_AD_BIND_PASSWORD
    ad_users_ou: str = "OU=Usuarios,OU=VALEVERDE,DC=infranoc,DC=lab"
    winrm_host: str = "192.168.56.10"
    winrm_user: str = "svc_infranoc@infranoc.lab"
    winrm_password: str = ""              # env INFRANOC_WINRM_PASSWORD
    ad_audit_interval_minutes: int = 15
    ad_tenant_id: str = "c0f64a7a-f821-4b23-97be-5a610afba0e0"  # env INFRANOC_AD_TENANT_ID
    # Prometheus (Fase 6 - Dashboard NOC)
    prometheus_url: str = "http://localhost:9090"
    # AI (Fase 7) entra depois


settings = Settings()