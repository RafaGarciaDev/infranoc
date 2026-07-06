from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# tenant atual (multi-tenancy) — populado pela dependency de auth
current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)
current_user_email: ContextVar[str | None] = ContextVar("current_user_email", default=None)


async def get_session() -> AsyncSession:
    async with SessionLocal() as s:
        yield s
