"""Cliente SSH para gestao de servidores Linux (Fase 9d).

Usa asyncssh com autenticacao por senha (decisao de laboratorio; em
producao/9a, trocar para chave dedicada com conta de servico).
"""
from __future__ import annotations

import asyncio

import asyncssh

from app.core.config import settings


class SshClient:
    def __init__(self, host: str | None = None, user: str | None = None, password: str | None = None):
        self.host = host or settings.linux_ssh_host
        self.user = user or settings.linux_ssh_user
        self.password = password or settings.linux_ssh_password

    async def run(self, cmd: str, timeout: int = 20) -> dict:
        async with asyncssh.connect(
            self.host,
            username=self.user,
            password=self.password,
            known_hosts=None,
        ) as conn:
            result = await asyncio.wait_for(conn.run(cmd, check=False), timeout=timeout)
            return {
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "exit_code": result.exit_status,
            }
