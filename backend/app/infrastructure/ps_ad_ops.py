"""
Cliente PowerShell Remoting para o modulo Active Directory (Fase 5).

Responsavel por operacoes que exigem canal seguro (WinRM), que o LDAP puro
nao cobre sem LDAPS configurado no lab:
- reset de senha (Set-ADAccountPassword)
- desbloqueio de conta (Unlock-ADAccount)

Seguranca:
- O `sam` e sempre validado contra um regex restrito antes de entrar em
  qualquer script PowerShell, para evitar injection (o script roda cru na DC).
- A senha nunca e logada e nunca e interpolada diretamente no texto do
  script. Ela e passada via `environment` do pypsrp.Client.execute_ps, que
  seta a variavel do lado do PowerShell usando cmdlets parametrizados
  (New-Item -Value ...) em vez de concatenacao de string — isso evita tanto
  injection quanto vazamento da senha no log interno do pypsrp (que loga
  apenas a chave da env var, nunca o valor).

Nota de API: pypsrp.client.Client.execute_ps NAO aceita um parametro
'arguments' (apesar de alguns exemplos antigos sugerirem isso) — os unicos
parametros sao script, configuration_name e environment. Usamos $env:...
dentro do script para ler os valores passados.
"""
import logging
import re

from pypsrp.client import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# sAMAccountName do AD: letras, numeros, ponto, underscore e hifen, ate 64 chars.
# Qualquer coisa fora disso e rejeitada antes de tocar o PowerShell Remoting.
_SAM_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _validate_sam(sam: str) -> str:
    if not _SAM_PATTERN.match(sam):
        raise ValueError(f"sAMAccountName invalido: {sam!r}")
    return sam


class PsAdOps:
    """Cliente fino sobre pypsrp, escopado a conta de servico svc_infranoc."""

    def _client(self) -> Client:
        # Nunca logar settings.winrm_password.
        return Client(
            settings.winrm_host,
            username=settings.winrm_user,
            password=settings.winrm_password,
            ssl=False,
            auth="basic",
            encryption="never",
        )

    def reset_password(self, sam: str, new_password: str, must_change: bool) -> None:
        """Reseta a senha, garante a conta habilitada e desbloqueada.

        A senha nunca aparece em nenhuma linha de log (nem no logger deste
        modulo, nem no log interno do pypsrp): apenas o `sam` e registrado
        (pela camada de auditoria da rota, nao aqui).
        """
        sam = _validate_sam(sam)

        change_clause = "true" if must_change else "false"

        script = f"""
        Import-Module ActiveDirectory
        $sam = $env:INFRANOC_AD_SAM
        $sec = ConvertTo-SecureString $env:INFRANOC_AD_NEWPWD -AsPlainText -Force
        Set-ADAccountPassword -Identity $sam -NewPassword $sec -Reset
        Enable-ADAccount -Identity $sam
        Set-ADUser -Identity $sam -ChangePasswordAtLogon ${change_clause}
        Unlock-ADAccount -Identity $sam
        """

        logger.info("Resetando senha (sam=%s, must_change=%s)", sam, must_change)

        with self._client() as c:
            out, streams, had_error = c.execute_ps(
                script,
                environment={
                    "INFRANOC_AD_SAM": sam,
                    "INFRANOC_AD_NEWPWD": new_password,
                },
            )
            if had_error:
                logger.error(
                    "Falha ao resetar senha de sam=%s: %s",
                    sam,
                    "; ".join(str(e) for e in streams.error),
                )
                raise RuntimeError("; ".join(str(e) for e in streams.error))

        logger.info("Senha resetada com sucesso (sam=%s)", sam)

    def unlock(self, sam: str) -> None:
        """Desbloqueia a conta (Unlock-ADAccount), sem alterar a senha."""
        sam = _validate_sam(sam)

        script = """
        Import-Module ActiveDirectory
        Unlock-ADAccount -Identity $env:INFRANOC_AD_SAM
        """

        logger.info("Desbloqueando conta (sam=%s)", sam)

        with self._client() as c:
            out, streams, had_error = c.execute_ps(
                script,
                environment={"INFRANOC_AD_SAM": sam},
            )
            if had_error:
                logger.error(
                    "Falha ao desbloquear sam=%s: %s",
                    sam,
                    "; ".join(str(e) for e in streams.error),
                )
                raise RuntimeError("; ".join(str(e) for e in streams.error))

        logger.info("Conta desbloqueada com sucesso (sam=%s)", sam)