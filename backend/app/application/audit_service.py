"""Servico de auditoria (Fase 5 - Bloco 5).

Grava entradas em AuditLog para toda escrita feita pelo modulo de Active
Directory (e, no futuro, por qualquer outro modulo que precise auditar).

Responsabilidade de seguranca: esta funcao NUNCA deve receber segredos
(senhas, tokens, etc.) em `details` ou `target` - quem chama .log(...) e
responsavel por garantir isso antes de chamar.

Fase 6b: adicionado parametro `tenant_id` opcional. Alguns chamadores (como
o webhook do AlertManager) resolvem o tenant pelo slug da URL e nao passam
pelo ContextVar current_tenant - para esses casos, o tenant deve ser passado
explicitamente, senao o log() antigo silenciosamente nao gravava nada.
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
    tenant_id: uuid.UUID | None = None,
) -> None:
    """Registra uma entrada de auditoria e persiste (commit) imediatamente.

    Se `tenant_id` for passado explicitamente, ele tem prioridade sobre o
    ContextVar current_tenant (necessario para contextos como webhooks que
    nao passam pelo middleware que popula o ContextVar).
    """
    if tenant_id is None:
        tenant_id_raw = current_tenant.get()
        if tenant_id_raw is None:
            logger.warning(
                "audit_service.log chamado sem tenant_id no contexto (action=%s, target=%s)",
                action,
                target,
            )
            return
        tenant_id = uuid.UUID(tenant_id_raw)

    entry = AuditLog(
        tenant_id=tenant_id,
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