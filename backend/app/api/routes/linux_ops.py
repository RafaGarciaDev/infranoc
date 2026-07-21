"""Linux Ops (Fase 9d) + Toolkit de Diagnostico (Fase 9e).

Gestao basica do servidor Linux MES01 via SSH (asyncssh), e ferramentas
simples de diagnostico de rede (port-check local, comandos remotos via SSH).
"""
from __future__ import annotations

import socket
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.application import audit_service
from app.core.db import get_session
from app.core.deps import require
from app.infrastructure.ssh_client import SshClient

router_linux = APIRouter(prefix="/linux", tags=["linux-ops"])
router_toolkit = APIRouter(prefix="/toolkit", tags=["toolkit"])

ssh = SshClient()

_ALLOWED_SYSTEMD_ACTIONS = {"start", "stop", "restart"}


class SnapshotOut(BaseModel):
    uptime: str
    who: str
    last: str


@router_linux.get("/snapshot", response_model=SnapshotOut)
async def linux_snapshot(claims: Annotated[dict, Depends(require("linux.read"))]) -> SnapshotOut:
    up = await ssh.run("uptime")
    who = await ssh.run("who")
    last = await ssh.run("last -n 10")
    return SnapshotOut(uptime=up["stdout"].strip(), who=who["stdout"].strip(), last=last["stdout"].strip())


class LinuxUserOut(BaseModel):
    username: str
    uid: str
    home: str
    shell: str


@router_linux.get("/users", response_model=list[LinuxUserOut])
async def linux_users(claims: Annotated[dict, Depends(require("linux.read"))]) -> list[LinuxUserOut]:
    result = await ssh.run("getent passwd")
    out: list[LinuxUserOut] = []
    for line in result["stdout"].splitlines():
        parts = line.split(":")
        if len(parts) < 7:
            continue
        try:
            uid = int(parts[2])
        except ValueError:
            continue
        if uid < 1000 or parts[0] == "nobody":
            continue
        out.append(LinuxUserOut(username=parts[0], uid=parts[2], home=parts[5], shell=parts[6]))
    return out


class SystemdUnitOut(BaseModel):
    unit: str
    load: str
    active: str
    sub: str
    description: str


@router_linux.get("/systemd", response_model=list[SystemdUnitOut])
async def linux_systemd(
    claims: Annotated[dict, Depends(require("linux.read"))],
    q: str | None = None,
) -> list[SystemdUnitOut]:
    result = await ssh.run("systemctl list-units --type=service --all --no-pager --no-legend --plain")
    out: list[SystemdUnitOut] = []
    for line in result["stdout"].splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        unit, load, active, sub, desc = parts
        if q and q.lower() not in unit.lower():
            continue
        out.append(SystemdUnitOut(unit=unit, load=load, active=active, sub=sub, description=desc))
    return out[:200]


class SystemdActionIn(BaseModel):
    unit: str
    action: str


@router_linux.post("/systemd/action")
async def linux_systemd_action(
    body: SystemdActionIn,
    claims: Annotated[dict, Depends(require("linux.exec"))],
    session=Depends(get_session),
) -> dict:
    if body.action not in _ALLOWED_SYSTEMD_ACTIONS:
        raise HTTPException(400, f"Acao invalida; use uma de {sorted(_ALLOWED_SYSTEMD_ACTIONS)}")
    result = await ssh.run(f"sudo -n systemctl {body.action} {body.unit}")
    await audit_service.log(session, f"linux.systemd.{body.action}", target=body.unit)
    if result["exit_code"] != 0:
        raise HTTPException(400, f"Falha ao executar (exit={result['exit_code']}): {result['stderr'] or result['stdout']}")
    return {"ok": True}


class DiskUsageOut(BaseModel):
    mount: str
    size: str
    used: str
    avail: str
    percent: str


@router_linux.get("/disk", response_model=list[DiskUsageOut])
async def linux_disk(claims: Annotated[dict, Depends(require("linux.read"))]) -> list[DiskUsageOut]:
    result = await ssh.run("df -h --output=target,size,used,avail,pcent")
    lines = result["stdout"].splitlines()
    out: list[DiskUsageOut] = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        mount, size, used, avail, pct = parts[0], parts[1], parts[2], parts[3], parts[4]
        out.append(DiskUsageOut(mount=mount, size=size, used=used, avail=avail, percent=pct))
    return out


class PortCheckIn(BaseModel):
    host: str
    port: int
    timeout: float = 3.0


class PortCheckOut(BaseModel):
    reachable: bool
    latency_ms: float | None


@router_toolkit.post("/port-check", response_model=PortCheckOut)
async def toolkit_port_check(
    body: PortCheckIn,
    claims: Annotated[dict, Depends(require("toolkit.exec"))],
    session=Depends(get_session),
) -> PortCheckOut:
    start = time.monotonic()
    reachable = False
    try:
        with socket.create_connection((body.host, body.port), timeout=body.timeout):
            reachable = True
    except OSError:
        reachable = False
    latency = (time.monotonic() - start) * 1000
    await audit_service.log(session, "toolkit.port-check", target=f"{body.host}:{body.port}")
    return PortCheckOut(reachable=reachable, latency_ms=round(latency, 1) if reachable else None)


class SsOut(BaseModel):
    output: str


@router_toolkit.get("/ss", response_model=SsOut)
async def toolkit_ss(claims: Annotated[dict, Depends(require("toolkit.exec"))]) -> SsOut:
    result = await ssh.run("ss -tulpn")
    return SsOut(output=result["stdout"])
