"""Cliente SNMP v2c (GET/SET) para ativos de rede/cyber reais (switches,
routers, firewalls, APs, impressoras, UPS - extensao real da Fase 9L, ver
ADR-007).

Segue o mesmo desenho do SshClient (app/infrastructure/ssh_client.py): classe
fina, aceita overrides no construtor, fallback pra settings. Diferenca chave:
nao ha um host fixo como no SSH/WinRM (que sempre miram DC01/MES01) - aqui o
host vem do Asset.ip_address de cada dispositivo, entao e sempre passado
explicitamente pelo chamador.
"""
from __future__ import annotations

import asyncio

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    Gauge32,
    Integer,
    ObjectIdentity,
    ObjectType,
    OctetString,
    SnmpEngine,
    UdpTransportTarget,
    Unsigned32,
    get_cmd,
    set_cmd,
)

from app.core.config import settings

_VALUE_TYPES = {
    "string": OctetString,
    "int": Integer,
    "gauge": Gauge32,
    "unsigned": Unsigned32,
}


class SnmpClient:
    def __init__(
        self,
        host: str,
        port: int = 161,
        community: str | None = None,
        timeout: int = 5,
        retries: int = 1,
    ):
        self.host = host
        self.port = port
        self.community = community or settings.snmp_community
        self.timeout = timeout
        self.retries = retries

    async def get(self, oid: str) -> str:
        engine = SnmpEngine()
        target = await UdpTransportTarget.create(
            (self.host, self.port), timeout=self.timeout, retries=self.retries
        )
        error_indication, error_status, _error_index, var_binds = await asyncio.wait_for(
            get_cmd(
                engine,
                CommunityData(self.community, mpModel=1),  # mpModel=1 -> SNMPv2c
                target,
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
            ),
            timeout=self.timeout + 5,
        )
        if error_indication:
            raise RuntimeError(f"SNMP GET falhou ({self.host}:{self.port} {oid}): {error_indication}")
        if error_status:
            raise RuntimeError(
                f"SNMP GET falhou ({self.host}:{self.port} {oid}): {error_status.prettyPrint()}"
            )
        _, value = var_binds[0]
        return str(value)

    async def set(self, oid: str, value: str, value_type: str = "string") -> str:
        py_type = _VALUE_TYPES.get(value_type, OctetString)
        engine = SnmpEngine()
        target = await UdpTransportTarget.create(
            (self.host, self.port), timeout=self.timeout, retries=self.retries
        )
        error_indication, error_status, _error_index, var_binds = await asyncio.wait_for(
            set_cmd(
                engine,
                CommunityData(self.community, mpModel=1),
                target,
                ContextData(),
                ObjectType(ObjectIdentity(oid), py_type(value)),
            ),
            timeout=self.timeout + 5,
        )
        if error_indication:
            raise RuntimeError(f"SNMP SET falhou ({self.host}:{self.port} {oid}): {error_indication}")
        if error_status:
            raise RuntimeError(
                f"SNMP SET falhou ({self.host}:{self.port} {oid}): {error_status.prettyPrint()}"
            )
        _, value_out = var_binds[0]
        return str(value_out)
