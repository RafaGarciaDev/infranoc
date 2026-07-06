"""Fixtures de teste do InfraNOC.

Usa testcontainers para subir um Postgres descartável e isolado durante os
testes de integração. Se o Docker/testcontainers não estiver disponível no
ambiente, as fixtures que dependem de banco são puladas (skip).

A fixture db_session recria o schema do zero a cada teste (drop_all +
create_all), garantindo isolamento total entre os testes.
"""

import asyncio

import pytest
import pytest_asyncio

try:
    from testcontainers.postgres import PostgresContainer

    _HAS_TC = True
except Exception:  # pragma: no cover
    _HAS_TC = False


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def pg_url():
    """Sobe um Postgres descartável e devolve a URL async. Skip se indisponível."""
    if not _HAS_TC:
        pytest.skip("testcontainers indisponível neste ambiente")
    try:
        with PostgresContainer("postgres:16") as pg:
            raw = pg.get_connection_url()  # postgresql+psycopg2://...
            async_url = raw.replace("+psycopg2", "+asyncpg").replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            yield async_url
    except Exception as e:  # pragma: no cover
        pytest.skip(f"não foi possível subir o Postgres de teste: {e}")


@pytest_asyncio.fixture
async def db_session(pg_url):
    """Schema limpo por teste: dropa e recria todas as tabelas, entrega sessão."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.domain.models import Base

    engine = create_async_engine(pg_url, echo=False)
    # isolamento: schema do zero a cada teste
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s

    await engine.dispose()
