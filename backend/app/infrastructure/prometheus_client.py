"""Cliente HTTP para a API de query do Prometheus.

Fase 6 - Dashboard NOC. Consultas instantaneas apenas (endpoint /api/v1/query).
Series ausentes retornam None (nao levantam) - o dashboard tolera linhas
paradas que somem de counters.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class PrometheusClient:
    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        self.base_url = (base_url or settings.prometheus_url).rstrip("/")
        self.timeout = timeout

    async def _query(self, expr: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/query"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(url, params={"query": expr})
                r.raise_for_status()
                payload = r.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("prometheus query falhou: expr=%r err=%s", expr, exc)
            return []

        if payload.get("status") != "success":
            logger.warning("prometheus retornou status=%s expr=%r", payload.get("status"), expr)
            return []
        return payload.get("data", {}).get("result", []) or []

    async def query_scalar(self, expr: str) -> float | None:
        """Retorna o primeiro valor da query como float, ou None se vazio.

        Uso tipico: agregacoes que produzem um unico valor
        (ex.: count(...), sum(...), infranoc_oee_percent{line="1"}).
        """
        result = await self._query(expr)
        if not result:
            return None
        try:
            return float(result[0]["value"][1])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("valor invalido em query %r: %s", expr, exc)
            return None

    async def query_vector(self, expr: str) -> list[tuple[dict[str, str], float]]:
        """Retorna todos os pontos (labels, valor). Util quando ha varias series."""
        out: list[tuple[dict[str, str], float]] = []
        for row in await self._query(expr):
            try:
                out.append((row.get("metric", {}), float(row["value"][1])))
            except (KeyError, IndexError, TypeError, ValueError):
                continue
        return out