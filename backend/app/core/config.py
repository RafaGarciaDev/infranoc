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
    ad_mock: bool = False                            # env INFRANOC_AD_MOCK
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
    # AI (Fase 7)
    ai_base_url: str = "http://localhost:11434"   # env INFRANOC_AI_BASE_URL
    ai_model: str = "qwen2.5:3b"                    # env INFRANOC_AI_MODEL


    # Peppermint (Fase 6b) - login via email/senha; token expira rapido, sem API key estatica
    peppermint_url: str = "http://localhost:5003"
    peppermint_email: str = "admin@valeverde.com"
    peppermint_password: str = ""         # env INFRANOC_PEPPERMINT_PASSWORD
    peppermint_client_id: str = ""        # env INFRANOC_PEPPERMINT_CLIENT_ID - Client ja cadastrado
    peppermint_default_email: str = "noc@valeverde.com"  # e-mail do 'solicitante' nos tickets automaticos

    # Vikunja (Fase 6b) - token de API estatico (gerado na UI, Settings -> API Tokens)
    vikunja_url: str = "http://localhost:3456"
    vikunja_token: str = ""               # env INFRANOC_VIKUNJA_TOKEN
    vikunja_project_id: int = 0           # env INFRANOC_VIKUNJA_PROJECT_ID

    # Automacao (Fase 6b)
    auto_ticket_min_severity: str = "warning"
    auto_task_min_severity: str = "critical"
    storm_window_seconds: int = 120
    storm_threshold: int = 10

settings = Settings()
