"""Cliente PowerShell Remoting (WinRM) generico (Fase 9n).

Consolida o padrao de conexao WinRM/pypsrp ja usado em devices.py
(_run_real_get_status) e ps_ad_ops.py (PsAdOps._client), com uma interface
analoga a SshClient.run() (Fase 9d) - async, retorna dict, sem exigir que
o chamador lide com run_in_threadpool (pypsrp e sincrono).

Nao reescreve devices.py/ps_ad_ops.py para usar este client - ambos ja
validados em producao contra a DC01 real, sem necessidade funcional
imediata de mudar sua implementacao.
"""
from __future__ import annotations

from fastapi.concurrency import run_in_threadpool
from pypsrp.client import Client

from app.core.config import settings


class WinRmClient:
    def __init__(self, host: str | None = None, user: str | None = None, password: str | None = None):
        self.host = host or settings.winrm_host
        self.user = user or settings.winrm_user
        self.password = password or settings.winrm_password

    def _client(self) -> Client:
        # Nunca logar self.password.
        return Client(
            self.host,
            username=self.user,
            password=self.password,
            ssl=False,
            auth="basic",
            encryption="never",
        )

    async def run_ps(self, script: str, environment: dict | None = None) -> dict:
        """Executa um script PowerShell via run_in_threadpool (pypsrp e sincrono).

        `environment` segue a convencao de ps_ad_ops.py: valores sensiveis
        devem ser passados aqui (lidos via $env:CHAVE no script), nunca
        interpolados diretamente na string do script.
        """
        def _call() -> dict:
            with self._client() as c:
                out, streams, had_error = c.execute_ps(script, environment=environment or {})
                return {
                    "stdout": (out or "").strip(),
                    "had_error": had_error,
                    "errors": [str(e) for e in streams.error] if had_error else [],
                }
        return await run_in_threadpool(_call)
