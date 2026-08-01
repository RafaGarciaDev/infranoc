"""Windows Server Ops (Fase 9n) - espelha Linux Ops (9d/9e) para Windows,
contra o servidor real PSA-TI-DC01 via WinRM.

Requer que a conta de servico (settings.winrm_user) tenha permissao de
administrador local no servidor - sem isso, WMI/SCM (usados aqui pra listar
e gerenciar servicos, disco e portas em escuta) retornam "Access denied"
mesmo com WinRM basico funcionando (confirmado via teste real: Get-Service,
Get-CimInstance e Get-NetTCPConnection falham com uma conta sem esse
privilegio, mesmo conseguindo rodar comandos simples como hostname/Get-Date).
"""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.application import audit_service
from app.core.db import get_session
from app.core.deps import require
from app.infrastructure.ps_ad_ops import PsAdOps
from app.infrastructure.winrm_client import WinRmClient

router_windows = APIRouter(prefix="/windows", tags=["windows-ops"])

winrm = WinRmClient()
ad_ops = PsAdOps()

_ALLOWED_SERVICE_ACTIONS = {"start", "stop", "restart"}


def _parse_json_list(text: str) -> list[dict]:
    text = (text or "").strip()
    if not text:
        return []
    data = json.loads(text)
    return [data] if isinstance(data, dict) else data


class RdpSessionOut(BaseModel):
    username: str
    session_name: str
    state: str
    idle_time: str
    logon_time: str


class SnapshotOut(BaseModel):
    caption: str
    last_boot: str
    hostname: str
    sessions: list[RdpSessionOut]


@router_windows.get("/snapshot", response_model=SnapshotOut)
async def windows_snapshot(claims: Annotated[dict, Depends(require("winserver.read"))]) -> SnapshotOut:
    result = await winrm.run_ps(
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object Caption,@{N='LastBootUpTime';E={$_.LastBootUpTime.ToString('u')}} | "
        "ConvertTo-Json -Compress; "
        "hostname"
    )
    if result["had_error"]:
        raise HTTPException(502, "; ".join(result["errors"]))
    lines = result["stdout"].splitlines()
    if not lines:
        raise HTTPException(502, "Resposta vazia do servidor")
    os_info = json.loads(lines[0])
    hostname = lines[-1].strip() if len(lines) > 1 else ""
    sessions = ad_ops.list_rdp_sessions()
    return SnapshotOut(
        caption=os_info.get("Caption", ""),
        last_boot=os_info.get("LastBootUpTime", ""),
        hostname=hostname,
        sessions=[RdpSessionOut(**s) for s in sessions],
    )


class WindowsUserOut(BaseModel):
    name: str
    enabled: bool


@router_windows.get("/users", response_model=list[WindowsUserOut])
async def windows_users(claims: Annotated[dict, Depends(require("winserver.read"))]) -> list[WindowsUserOut]:
    # Usuarios LOCAIS do servidor - distinto da tela de usuarios do dominio AD
    # (Fase 5/9c), que ja cobre contas de dominio.
    result = await winrm.run_ps(
        "Get-LocalUser | Select-Object Name,Enabled | ConvertTo-Json -Compress"
    )
    if result["had_error"]:
        raise HTTPException(502, "; ".join(result["errors"]))
    data = _parse_json_list(result["stdout"])
    return [WindowsUserOut(name=d["Name"], enabled=bool(d["Enabled"])) for d in data]


class WindowsServiceOut(BaseModel):
    name: str
    display_name: str
    status: str
    start_type: str


@router_windows.get("/services", response_model=list[WindowsServiceOut])
async def windows_services(
    claims: Annotated[dict, Depends(require("winserver.read"))],
    q: str | None = None,
) -> list[WindowsServiceOut]:
    result = await winrm.run_ps(
        "Get-Service | Select-Object Name,DisplayName,"
        "@{N='Status';E={$_.Status.ToString()}},@{N='StartType';E={$_.StartType.ToString()}} "
        "| ConvertTo-Json -Compress"
    )
    if result["had_error"]:
        raise HTTPException(502, "; ".join(result["errors"]))
    data = _parse_json_list(result["stdout"])
    out = [
        WindowsServiceOut(
            name=d["Name"], display_name=d["DisplayName"],
            status=str(d["Status"]), start_type=str(d["StartType"]),
        )
        for d in data
    ]
    if q:
        ql = q.lower()
        out = [s for s in out if ql in s.name.lower() or ql in s.display_name.lower()]
    return out[:200]


class ServiceActionIn(BaseModel):
    name: str
    action: str


@router_windows.post("/services/action")
async def windows_service_action(
    body: ServiceActionIn,
    claims: Annotated[dict, Depends(require("winserver.exec"))],
    session=Depends(get_session),
) -> dict:
    if body.action not in _ALLOWED_SERVICE_ACTIONS:
        raise HTTPException(400, f"Acao invalida; use uma de {sorted(_ALLOWED_SERVICE_ACTIONS)}")
    cmdlet = {"start": "Start-Service", "stop": "Stop-Service", "restart": "Restart-Service"}[body.action]
    result = await winrm.run_ps(
        f"{cmdlet} -Name $env:INFRANOC_WIN_SVC_NAME -ErrorAction Stop",
        environment={"INFRANOC_WIN_SVC_NAME": body.name},
    )
    await audit_service.log(session, f"windows.service.{body.action}", target=body.name)
    if result["had_error"]:
        raise HTTPException(400, f"Falha ao executar: {'; '.join(result['errors'])}")
    return {"ok": True}


class DiskUsageOut(BaseModel):
    drive: str
    size_gb: float
    free_gb: float
    percent_used: float


@router_windows.get("/disk", response_model=list[DiskUsageOut])
async def windows_disk(claims: Annotated[dict, Depends(require("winserver.read"))]) -> list[DiskUsageOut]:
    result = await winrm.run_ps(
        "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | "
        "Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json -Compress"
    )
    if result["had_error"]:
        raise HTTPException(502, "; ".join(result["errors"]))
    data = _parse_json_list(result["stdout"])
    out = []
    for d in data:
        size = float(d["Size"] or 0)
        free = float(d["FreeSpace"] or 0)
        used_pct = round(((size - free) / size) * 100, 1) if size else 0.0
        out.append(DiskUsageOut(
            drive=d["DeviceID"],
            size_gb=round(size / (1024 ** 3), 1),
            free_gb=round(free / (1024 ** 3), 1),
            percent_used=used_pct,
        ))
    return out


class NetConnOut(BaseModel):
    output: str


@router_windows.get("/netstat", response_model=NetConnOut)
async def windows_netstat(claims: Annotated[dict, Depends(require("winserver.read"))]) -> NetConnOut:
    # Equivalente ao "ss -tulpn" do linux_ops.py - fica no router windows,
    # nao no toolkit generico (mesma decisao ja tomada pro "ss" do Linux).
    result = await winrm.run_ps(
        "Get-NetTCPConnection -State Listen | "
        "Select-Object LocalAddress,LocalPort,OwningProcess | Format-Table -AutoSize | Out-String"
    )
    if result["had_error"]:
        raise HTTPException(502, "; ".join(result["errors"]))
    return NetConnOut(output=result["stdout"])
