from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# --- InfraNOC: importar settings e metadata dos modelos ---
from app.core.config import settings
from app.domain.models import Base

# Alembic Config object (lê o alembic.ini)
config = context.config

# Alembic roda de forma SÍNCRONA; nossa app usa asyncpg.
# Convertemos "postgresql+asyncpg://" -> "postgresql://" só para as migrations.
sync_url = settings.database_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_url)

# Logging a partir do arquivo de config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo para o autogenerate (todas as tabelas declaradas em models.py)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Migrations em modo 'offline' (gera SQL sem conectar)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migrations em modo 'online' (conecta no banco e aplica)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
