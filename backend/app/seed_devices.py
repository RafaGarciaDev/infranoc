"""Seed do Console de Gestao de Dispositivos (Fase 9L) - catalogo de
comandos e perfis de protocolo por ativo do CMDB.

Pros 2 ativos reais do lab (PSA-TI-DC01, PSA-OT-MES01) is_real=True.
Para os demais (~642 ativos simulados), is_real=False - ver ADR-006.

Rodar:  uv run python -m app.seed_devices
"""

import asyncio
import uuid

from sqlalchemy import select

from app.core.db import SessionLocal
from app.domain.enums import AssetType
from app.domain.models import (
    Asset,
    DeviceCommand,
    DeviceCommandKind,
    DeviceProtocol,
    DeviceProtocolProfile,
)

REAL_ASSET_NAMES = {"PSA-TI-DC01", "PSA-OT-MES01"}

# Tipo de ativo -> (protocolo, porta padrao). Cobre os 27 tipos do enum
# AssetType; nem todos tem comandos no catalogo curado abaixo ainda (a
# cobertura de comandos e incremental, igual as 12 regras do ADR-004).
TYPE_PROTOCOL: dict[AssetType, tuple[DeviceProtocol, int | None]] = {
    AssetType.Server: (DeviceProtocol.SSH, 22),
    AssetType.Workstation: (DeviceProtocol.WinRM, 5985),
    AssetType.Laptop: (DeviceProtocol.WinRM, 5985),
    AssetType.NetworkSwitch: (DeviceProtocol.SNMP, 161),
    AssetType.Router: (DeviceProtocol.SNMP, 161),
    AssetType.Firewall: (DeviceProtocol.SNMP, 161),
    AssetType.AccessPoint: (DeviceProtocol.SNMP, 161),
    AssetType.Printer: (DeviceProtocol.SNMP, 161),
    AssetType.UPS: (DeviceProtocol.SNMP, 161),
    AssetType.Generator: (DeviceProtocol.SNMP, 161),
    AssetType.ACUnit: (DeviceProtocol.SNMP, 161),
    AssetType.PLC: (DeviceProtocol.Modbus, 502),
    AssetType.HMI: (DeviceProtocol.HTTPAPI, None),
    AssetType.SCADA: (DeviceProtocol.HTTPAPI, None),
    AssetType.Sensor: (DeviceProtocol.Modbus, 502),
    AssetType.Scale: (DeviceProtocol.Modbus, 502),
    AssetType.Camera: (DeviceProtocol.HTTPAPI, None),
    AssetType.NVR: (DeviceProtocol.HTTPAPI, None),
    AssetType.Phone: (DeviceProtocol.HTTPAPI, None),
    AssetType.StorageArray: (DeviceProtocol.SSH, 22),
    AssetType.TapeLibrary: (DeviceProtocol.SNMP, 161),
    AssetType.Motor: (DeviceProtocol.Modbus, 502),
    AssetType.Tank: (DeviceProtocol.Modbus, 502),
    AssetType.AirCompressor: (DeviceProtocol.Modbus, 502),
    AssetType.SteamBoiler: (DeviceProtocol.Modbus, 502),
    AssetType.ChilledWaterPump: (DeviceProtocol.Modbus, 502),
    AssetType.BarcodeReader: (DeviceProtocol.HTTPAPI, None),
    AssetType.Other: (DeviceProtocol.HTTPAPI, None),
}

# Catalogo curado de comandos (asset_type, protocol, name, kind, requires_permission).
# Nao cobre "todos os comandos possiveis" de todo fabricante - so um conjunto
# inicial representativo, igual foi feito com as 12 regras do SIEM (ADR-004).
COMMANDS: list[tuple[AssetType, DeviceProtocol, str, DeviceCommandKind, str]] = [
    (AssetType.Server, DeviceProtocol.SSH, "get_status", DeviceCommandKind.Read, "devices.read"),
    (AssetType.Server, DeviceProtocol.SSH, "restart_service", DeviceCommandKind.Action, "devices.action"),
    (AssetType.Server, DeviceProtocol.WinRM, "get_status", DeviceCommandKind.Read, "devices.read"),
    (AssetType.Server, DeviceProtocol.WinRM, "restart_service", DeviceCommandKind.Action, "devices.action"),
    (AssetType.NetworkSwitch, DeviceProtocol.SNMP, "get_status", DeviceCommandKind.Read, "devices.read"),
    (AssetType.NetworkSwitch, DeviceProtocol.SNMP, "restart", DeviceCommandKind.Action, "devices.action"),
    (AssetType.Router, DeviceProtocol.SNMP, "get_status", DeviceCommandKind.Read, "devices.read"),
    (AssetType.Router, DeviceProtocol.SNMP, "restart", DeviceCommandKind.Action, "devices.action"),
    (AssetType.AccessPoint, DeviceProtocol.SNMP, "get_status", DeviceCommandKind.Read, "devices.read"),
    (AssetType.AccessPoint, DeviceProtocol.SNMP, "restart", DeviceCommandKind.Action, "devices.action"),
    (AssetType.Printer, DeviceProtocol.SNMP, "get_toner_level", DeviceCommandKind.Read, "devices.read"),
    (AssetType.Printer, DeviceProtocol.SNMP, "restart", DeviceCommandKind.Action, "devices.action"),
    (AssetType.UPS, DeviceProtocol.SNMP, "get_battery_level", DeviceCommandKind.Read, "devices.read"),
    (AssetType.Camera, DeviceProtocol.HTTPAPI, "get_status", DeviceCommandKind.Read, "devices.read"),
    (AssetType.Camera, DeviceProtocol.HTTPAPI, "restart", DeviceCommandKind.Action, "devices.action"),
    (AssetType.PLC, DeviceProtocol.Modbus, "get_status", DeviceCommandKind.Read, "devices.read"),
]


async def seed_devices(tenant_id: uuid.UUID) -> tuple[int, int]:
    async with SessionLocal() as session:
        existing = (
            await session.execute(
                select(DeviceProtocolProfile).where(DeviceProtocolProfile.tenant_id == tenant_id)
            )
        ).scalars().first()
        if existing:
            print("Ja existem perfis de protocolo para este tenant - abortando (evita duplicar).")
            return 0, 0

        # --- Catalogo de comandos (global, nao e por-tenant) ---
        existing_cmd_keys = set(
            (
                await session.execute(
                    select(DeviceCommand.asset_type, DeviceCommand.protocol, DeviceCommand.name)
                )
            ).all()
        )
        cmd_count = 0
        for asset_type, protocol, name, kind, perm in COMMANDS:
            key = (asset_type.value, protocol, name)
            if key in existing_cmd_keys:
                continue
            session.add(DeviceCommand(
                asset_type=asset_type.value,
                protocol=protocol,
                name=name,
                kind=kind,
                requires_permission=perm,
            ))
            cmd_count += 1

        # --- Perfis de protocolo (um por ativo do CMDB) ---
        assets = (
            await session.execute(select(Asset).where(Asset.tenant_id == tenant_id))
        ).scalars().all()

        profile_count = 0
        for asset in assets:
            mapping = TYPE_PROTOCOL.get(asset.type)
            if not mapping:
                continue
            protocol, port = mapping
            is_real = asset.name in REAL_ASSET_NAMES
            # DC01 e Windows Server (WinRM), nao Linux (SSH) - o mapeamento
            # generico por AssetType nao diferencia SO dentro do tipo "Server".
            if asset.name == "PSA-TI-DC01":
                protocol, port = DeviceProtocol.WinRM, 5985
            session.add(DeviceProtocolProfile(
                tenant_id=tenant_id,
                asset_id=asset.id,
                protocol=protocol,
                is_real=is_real,
                port=port,
            ))
            profile_count += 1

        await session.commit()
        print(f"OK: {cmd_count} comandos no catalogo, {profile_count} perfis de protocolo criados.")
        return cmd_count, profile_count


async def main() -> None:
    async with SessionLocal() as session:
        tenant_ids = (await session.execute(select(Asset.tenant_id).distinct())).scalars().all()
    for tid in tenant_ids:
        await seed_devices(tid)


if __name__ == "__main__":
    asyncio.run(main())
