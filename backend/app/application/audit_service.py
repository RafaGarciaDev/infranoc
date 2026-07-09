"""Servico de auditoria (Fase 5 - Bloco 5).

Grava entradas em AuditLog para toda escrita feita pelo modulo de Active
Directory (e, no futuro, por qualquer outro modulo que precise auditar).

Responsabilidade de seguranca: esta funcao NUNCA deve receber segredos
(senhas, tokens, etc.) em `details` ou `target` — quem chama .log(...) e
responsavel por garantir isso antes de chamar.
"""
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import current_tenant, current_user_email
from app.domain.models import AuditLog

logger = logging.getLogger(__name__)


async def log(
    session: AsyncSession,
    action: str,
    target: str | None = None,
    details: str | None = None,
    ip: str | None = None,
) -> None:
    """Registra uma entrada de auditoria e persiste (commit) imediatamente."""
    tenant_id_raw = current_tenant.get()
    if tenant_id_raw is None:
        # Nao deveria acontecer em uso normal (get_current_claims sempre seta
        # o tenant antes de qualquer rota autenticada rodar), mas nao derruba
        # a operacao principal por causa disso — so registra o problema.
        logger.warning(
            "audit_service.log chamado sem tenant_id no contexto (action=%s, target=%s)",
            action,
            target,
        )
        return

    entry = AuditLog(
        tenant_id=uuid.UUID(tenant_id_raw),
        action=action,
        target=target,
        actor_email=current_user_email.get(),
        details=details,
        ip=ip,
    )
    session.add(entry)
    await session.commit()
    logger.info(
        "Audit log registrado: action=%s target=%s actor=%s",
        action,
        target,
        entry.actor_email,
    )