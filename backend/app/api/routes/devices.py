"""Console de Gestao de Dispositivos (Fase 9L).

Para os ~644 ativos simulados do CMDB, os comandos sao simulados (ver
ADR-006) - mesma filosofia do ADR-003/004/005. Para os 2 ativos reais do
lab (PSA-TI-DC01, PSA-OT-MES01), o comando "get_status" e genuinamente
real, reaproveitando o SshClient (9d) e credenciais WinRM (Fase 5).

SNMP (ver ADR-007) estende isso: qualquer comando Read com "oid" cadastrado
no catalogo roda de verdade quando o perfil e is_real=True, nao so
"get_status" - reaproveitando o SnmpClient. Comandos de acao (kind="action")
continuam simulados por padrao para todos os protocolos (ADR-006); a unica
excecao e SNMP SET quando uma trava dupla e satisfeita (is_real +
allow_real_snmp_set no perfil, + permissao devices.snmp.set no operador -
ver _try_run_real).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from pypsrp.client import Client as WinRmClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import audit_service
from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_current_claims, require
from app.domain.models import (
    Asset,
    DeviceCommand,
    DeviceCommandExecution,
    DeviceCommandKind,
    DeviceCommandStatus,
    DeviceProtocol,
    DeviceProtocolProfile,
)
from app.infrastructure.snmp_client import SnmpClient
from app.infrastructure.ssh_client import SshClient

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceAssetOut(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str
    protocol: str
    is_real: bool
    port: int | None
    allow_real_snmp_set: bool


@router.get(
    "/assets",
    response_model=list[DeviceAssetOut],
    dependencies=[Depends(require("devices.read"))],
)
async def list_device_assets(
    claims: Annotated[dict, Depends(get_current_claims)],
    session: Annotated[AsyncSession, Depends(get_session)],
    only_real: bool = False,
) -> list[DeviceAssetOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(DeviceProtocolProfile, Asset)
        .join(Asset, Asset.id == DeviceProtocolProfile.asset_id)
        .where(DeviceProtocolProfile.tenant_id == tenant_id)
    )
    if only_real:
        stmt = stmt.where(DeviceProtocolProfile.is_real.is_(True))
    stmt = stmt.order_by(Asset.name)
    rows = (await session.execute(stmt)).all()
    return [
        DeviceAssetOut(
            asset_id=str(asset.id),
            asset_name=asset.name,
            asset_type=asset.type.value,
            protocol=profile.protocol.value,
            is_real=profile.is_real,
            port=profile.port,
            allow_real_snmp_set=profile.allow_real_snmp_set,
        )
        for profile, asset in rows
    ]


class DeviceCommandOut(BaseModel):
    id: str
    name: str
    kind: str
    requires_permission: str
    oid: str | None
    value_type: str | None


@router.get(
    "/assets/{asset_id}/commands",
    response_model=list[DeviceCommandOut],
    dependencies=[Depends(require("devices.read"))],
)
async def list_asset_commands(
    asset_id: str,
    claims: Annotated[dict, Depends(get_current_claims)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[DeviceCommandOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    profile = (
        await session.execute(
            select(DeviceProtocolProfile).where(
                DeviceProtocolProfile.tenant_id == tenant_id,
                DeviceProtocolProfile.asset_id == uuid.UUID(asset_id),
            )
        )
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Perfil de protocolo nao encontrado para este ativo")

    asset = await session.get(Asset, uuid.UUID(asset_id))
    if not asset:
        raise HTTPException(404, "Ativo nao encontrado")

    commands = (
        await session.execute(
            select(DeviceCommand).where(
                DeviceCommand.asset_type == asset.type.value,
                DeviceCommand.protocol == profile.protocol,
            )
        )
    ).scalars().all()
    return [
        DeviceCommandOut(
            id=str(c.id),
            name=c.name,
            kind=c.kind.value,
            requires_permission=c.requires_permission,
            oid=c.oid,
            value_type=c.value_type,
        )
        for c in commands
    ]


def _run_simulated(command_name: str, asset_name: str) -> str:
    """Gera uma resposta simulada plausivel - nao conecta em nada de verdade."""
    fakes = {
        "get_status": f"{asset_name}: status OK (simulado)",
        "restart": f"{asset_name}: reiniciado com sucesso (simulado)",
        "restart_service": f"{asset_name}: servico reiniciado com sucesso (simulado)",
        "get_toner_level": f"{asset_name}: nivel de toner 62% (simulado)",
        "get_battery_level": f"{asset_name}: bateria 94% (simulado)",
    }
    return fakes.get(command_name, f"{asset_name}: comando '{command_name}' executado (simulado)")


async def _run_real_get_status(protocol: DeviceProtocol) -> str:
    """Executa 'get_status' de verdade nos 2 ativos reais do lab."""
    if protocol == DeviceProtocol.SSH:
        result = await SshClient().run("uptime && systemctl is-system-running", timeout=10)
        return (result["stdout"] or result["stderr"] or "").strip() or "(sem saida)"

    if protocol == DeviceProtocol.WinRM:
        def _call() -> str:
            with WinRmClient(
                settings.winrm_host,
                username=settings.winrm_user,
                password=settings.winrm_password,
                ssl=False,
                auth="basic",
                encryption="never",
            ) as c:
                # Get-Service exige acesso ao Service Control Manager remoto, que a
                # conta svc_infranoc nao tem - trocado por comandos que so exigem
                # WinRM basico (confirmado via teste real).
                out, streams, had_error = c.execute_ps(
                    "(Get-Date).ToString(); hostname"
                )
                if had_error:
                    raise RuntimeError("; ".join(str(e) for e in streams.error))
                return (out or "").strip()
        return await run_in_threadpool(_call)

    raise RuntimeError(f"get_status real nao implementado para protocolo {protocol}")


async def _run_real_snmp_get(profile: DeviceProtocolProfile, asset: Asset, command: DeviceCommand) -> str:
    """Executa um GET SNMP de verdade, usando o OID cadastrado no catalogo."""
    if not command.oid:
        raise RuntimeError(f"Comando '{command.name}' nao tem OID cadastrado - GET real indisponivel")
    if not asset.ip_address:
        raise RuntimeError(f"Ativo '{asset.name}' nao tem ip_address cadastrado no CMDB")
    client = SnmpClient(host=asset.ip_address, port=profile.port or 161)
    return await client.get(command.oid)


async def _run_real_snmp_set(
    profile: DeviceProtocolProfile, asset: Asset, command: DeviceCommand, value: str | None,
) -> str:
    """Executa um SET SNMP de verdade. So e chamada quando a trava dupla do
    ADR-007 ja foi satisfeita pelo chamador (is_real + allow_real_snmp_set +
    permissao devices.snmp.set)."""
    if value is None or value == "":
        raise RuntimeError(f"Comando '{command.name}' exige um valor (SNMP SET)")
    if not command.oid:
        raise RuntimeError(f"Comando '{command.name}' nao tem OID cadastrado - SET real indisponivel")
    if not asset.ip_address:
        raise RuntimeError(f"Ativo '{asset.name}' nao tem ip_address cadastrado no CMDB")
    client = SnmpClient(host=asset.ip_address, port=profile.port or 161)
    return await client.set(command.oid, value, command.value_type or "string")


def _snmp_set_real_liberado(profile: DeviceProtocolProfile, command: DeviceCommand) -> bool:
    """Trava dupla do ADR-007: SET SNMP real so roda quando o ativo tem
    is_real=True E allow_real_snmp_set=True (opt-in explicito por ativo).
    A permissao devices.snmp.set (opt-in por operador) e checada a parte, no
    endpoint HTTP, antes de chegar aqui."""
    return (
        profile.is_real
        and profile.allow_real_snmp_set
        and profile.protocol == DeviceProtocol.SNMP
        and command.kind == DeviceCommandKind.Action
        and bool(command.oid)
    )


async def _try_run_real(
    profile: DeviceProtocolProfile, asset: Asset, command: DeviceCommand, value: str | None = None,
) -> str | None:
    """Tenta executar de verdade. Retorna None se nao ha "receita" real para
    esse (protocolo, comando) - nesse caso o chamador cai pro simulado.
    Uma excecao aqui vira status Error (ha receita real, mas ela falhou)."""
    if command.kind == DeviceCommandKind.Read:
        if profile.protocol == DeviceProtocol.SNMP and command.oid:
            return await _run_real_snmp_get(profile, asset, command)
        if profile.protocol in (DeviceProtocol.SSH, DeviceProtocol.WinRM) and command.name == "get_status":
            return await _run_real_get_status(profile.protocol)
        return None

    # kind == Action - ADR-006: acoes reais continuam bloqueadas por padrao
    # pra todos os protocolos. Unica excecao (ADR-007): SNMP SET com a trava
    # dupla satisfeita.
    if _snmp_set_real_liberado(profile, command):
        return await _run_real_snmp_set(profile, asset, command, value)
    return None


class ExecuteResultOut(BaseModel):
    id: str
    command_name: str
    status: str
    output: str | None
    executed_at: datetime


class ExecuteCommandIn(BaseModel):
    value: str | None = None


@router.post(
    "/assets/{asset_id}/commands/{command_id}/execute",
    response_model=ExecuteResultOut,
)
async def execute_device_command(
    asset_id: str,
    command_id: str,
    claims: Annotated[dict, Depends(get_current_claims)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: ExecuteCommandIn | None = None,
) -> ExecuteResultOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    value = body.value if body else None

    profile = (
        await session.execute(
            select(DeviceProtocolProfile).where(
                DeviceProtocolProfile.tenant_id == tenant_id,
                DeviceProtocolProfile.asset_id == uuid.UUID(asset_id),
            )
        )
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Perfil de protocolo nao encontrado para este ativo")

    asset = await session.get(Asset, uuid.UUID(asset_id))
    if not asset or asset.tenant_id != tenant_id:
        raise HTTPException(404, "Ativo nao encontrado")

    command = await session.get(DeviceCommand, uuid.UUID(command_id))
    if not command or command.asset_type != asset.type.value or command.protocol != profile.protocol:
        raise HTTPException(404, "Comando nao encontrado ou incompativel com este ativo")

    have_perms = set(claims.get("perm", []))
    if command.requires_permission not in have_perms:
        raise HTTPException(403, "Sem permissao para executar este comando")

    # ADR-007: SNMP SET real exige, alem da permissao do comando (devices.action),
    # a permissao extra devices.snmp.set - segunda metade da trava dupla (a
    # primeira, allow_real_snmp_set, e checada dentro de _try_run_real).
    if profile.is_real and _snmp_set_real_liberado(profile, command) and "devices.snmp.set" not in have_perms:
        raise HTTPException(403, "Sem permissao para executar SET real (devices.snmp.set)")

    try:
        real_output = await _try_run_real(profile, asset, command, value) if profile.is_real else None
        if real_output is not None:
            output = real_output
            status_ = DeviceCommandStatus.Success
        else:
            output = _run_simulated(command.name, asset.name)
            status_ = DeviceCommandStatus.Simulated
    except Exception as e:
        output = str(e)
        status_ = DeviceCommandStatus.Error

    execution = DeviceCommandExecution(
        tenant_id=tenant_id,
        asset_id=asset.id,
        command_id=command.id,
        status=status_,
        output=output,
        created_by=claims.get("sub"),
    )
    session.add(execution)
    await audit_service.log(
        session, "devices.command.execute",
        target=f"{asset.name}:{command.name}", tenant_id=tenant_id,
    )
    await session.commit()
    await session.refresh(execution)

    return ExecuteResultOut(
        id=str(execution.id),
        command_name=command.name,
        status=status_.value,
        output=output,
        executed_at=execution.created_at,
    )


class ExecutionOut(BaseModel):
    command_name: str
    status: str
    output: str | None
    executed_at: datetime
    executed_by: str | None


@router.get(
    "/assets/{asset_id}/executions",
    response_model=list[ExecutionOut],
    dependencies=[Depends(require("devices.read"))],
)
async def list_asset_executions(
    asset_id: str,
    claims: Annotated[dict, Depends(get_current_claims)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 50,
) -> list[ExecutionOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(DeviceCommandExecution, DeviceCommand)
        .join(DeviceCommand, DeviceCommand.id == DeviceCommandExecution.command_id)
        .where(
            DeviceCommandExecution.tenant_id == tenant_id,
            DeviceCommandExecution.asset_id == uuid.UUID(asset_id),
        )
        .order_by(DeviceCommandExecution.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        ExecutionOut(
            command_name=cmd.name,
            status=ex.status.value,
            output=ex.output,
            executed_at=ex.created_at,
            executed_by=ex.created_by,
        )
        for ex, cmd in rows
    ]
