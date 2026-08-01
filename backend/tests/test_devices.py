from unittest.mock import AsyncMock, patch

import pytest

from app.api.routes.devices import ExecuteCommandIn, execute_device_command
from app.domain.enums import AssetType, Layer
from app.domain.models import (
    Asset,
    DeviceCommand,
    DeviceCommandKind,
    DeviceProtocol,
    DeviceProtocolProfile,
    Permission,
    Tenant,
)


async def _seed_device(
    session,
    *,
    asset_type: AssetType = AssetType.NetworkSwitch,
    protocol: DeviceProtocol = DeviceProtocol.SNMP,
    command_name: str = "get_status",
    command_kind: DeviceCommandKind = DeviceCommandKind.Read,
    oid: str | None = "1.3.6.1.2.1.1.3.0",
    value_type: str | None = None,
    is_real: bool = False,
    allow_real_snmp_set: bool = False,
    ip_address: str | None = "10.0.0.50",
    requires_permission: str = "devices.read",
    extra_perms: tuple[str, ...] = (),
):
    tenant = Tenant(name="Vale Verde", slug="vv", active=True)
    session.add(tenant)
    await session.flush()

    for key in {"devices.read", "devices.action", "devices.snmp.set", requires_permission}:
        session.add(Permission(key=key, description=key))
    await session.flush()

    asset = Asset(
        tenant_id=tenant.id,
        name="SW-TESTE-01",
        type=asset_type,
        layer=Layer.TI,
        site="PSA",
        ip_address=ip_address,
    )
    session.add(asset)
    await session.flush()

    profile = DeviceProtocolProfile(
        tenant_id=tenant.id,
        asset_id=asset.id,
        protocol=protocol,
        is_real=is_real,
        allow_real_snmp_set=allow_real_snmp_set,
        port=161,
    )
    session.add(profile)

    command = DeviceCommand(
        asset_type=asset_type.value,
        protocol=protocol,
        name=command_name,
        kind=command_kind,
        requires_permission=requires_permission,
        oid=oid,
        value_type=value_type,
    )
    session.add(command)
    await session.commit()

    claims = {
        "tenant_id": str(tenant.id),
        "sub": "tester@vv.com",
        "perm": ["devices.read", "devices.action", *extra_perms],
    }
    return asset, profile, command, claims


@pytest.mark.asyncio
async def test_get_status_simulado_quando_is_real_false(db_session):
    asset, _profile, command, claims = await _seed_device(db_session, is_real=False)
    result = await execute_device_command(str(asset.id), str(command.id), claims, db_session)
    assert result.status == "simulated"


@pytest.mark.asyncio
async def test_snmp_get_real_quando_is_real_true_usa_oid(db_session):
    asset, _profile, command, claims = await _seed_device(db_session, is_real=True)
    with patch("app.api.routes.devices.SnmpClient") as MockClient:
        MockClient.return_value.get = AsyncMock(return_value="12345")
        result = await execute_device_command(str(asset.id), str(command.id), claims, db_session)
    assert result.status == "success"
    assert result.output == "12345"
    MockClient.assert_called_once_with(host="10.0.0.50", port=161)


@pytest.mark.asyncio
async def test_snmp_get_sem_oid_cai_simulado_mesmo_is_real(db_session):
    asset, _profile, command, claims = await _seed_device(db_session, is_real=True, oid=None)
    result = await execute_device_command(str(asset.id), str(command.id), claims, db_session)
    assert result.status == "simulated"


@pytest.mark.asyncio
async def test_snmp_get_real_erro_vira_status_error(db_session):
    asset, _profile, command, claims = await _seed_device(db_session, is_real=True)
    with patch("app.api.routes.devices.SnmpClient") as MockClient:
        MockClient.return_value.get = AsyncMock(side_effect=RuntimeError("timeout"))
        result = await execute_device_command(str(asset.id), str(command.id), claims, db_session)
    assert result.status == "error"
    assert "timeout" in result.output


@pytest.mark.asyncio
async def test_acao_permanece_simulada_mesmo_com_is_real_true(db_session):
    asset, _profile, command, claims = await _seed_device(
        db_session,
        command_name="restart",
        command_kind=DeviceCommandKind.Action,
        oid=None,
        is_real=True,
        requires_permission="devices.action",
    )
    with patch("app.api.routes.devices.SnmpClient") as MockClient:
        result = await execute_device_command(str(asset.id), str(command.id), claims, db_session)
    MockClient.assert_not_called()
    assert result.status == "simulated"


@pytest.mark.asyncio
async def test_sem_permissao_da_403(db_session):
    from fastapi import HTTPException

    asset, _profile, command, claims = await _seed_device(db_session, requires_permission="devices.read")
    claims = {**claims, "perm": []}
    with pytest.raises(HTTPException) as exc_info:
        await execute_device_command(str(asset.id), str(command.id), claims, db_session)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_snmp_get_real_sem_ip_address_vira_status_error(db_session):
    asset, _profile, command, claims = await _seed_device(db_session, is_real=True, ip_address=None)
    result = await execute_device_command(str(asset.id), str(command.id), claims, db_session)
    assert result.status == "error"
    assert "ip_address" in result.output


def _set_kwargs():
    return dict(
        command_name="set_port_admin_status",
        command_kind=DeviceCommandKind.Action,
        oid="1.3.6.1.2.1.2.2.1.7.1",
        value_type="int",
        requires_permission="devices.action",
    )


@pytest.mark.asyncio
async def test_snmp_set_bloqueado_por_padrao_mesmo_is_real(db_session):
    """allow_real_snmp_set=False (default) - trava dupla do ADR-007 nao satisfeita."""
    asset, _profile, command, claims = await _seed_device(
        db_session, is_real=True, allow_real_snmp_set=False, extra_perms=("devices.snmp.set",), **_set_kwargs(),
    )
    with patch("app.api.routes.devices.SnmpClient") as MockClient:
        result = await execute_device_command(
            str(asset.id), str(command.id), claims, db_session, ExecuteCommandIn(value="2"),
        )
    MockClient.assert_not_called()
    assert result.status == "simulated"


@pytest.mark.asyncio
async def test_snmp_set_real_liberado_com_trava_dupla(db_session):
    asset, _profile, command, claims = await _seed_device(
        db_session, is_real=True, allow_real_snmp_set=True, extra_perms=("devices.snmp.set",), **_set_kwargs(),
    )
    with patch("app.api.routes.devices.SnmpClient") as MockClient:
        MockClient.return_value.set = AsyncMock(return_value="2")
        result = await execute_device_command(
            str(asset.id), str(command.id), claims, db_session, ExecuteCommandIn(value="2"),
        )
    assert result.status == "success"
    assert result.output == "2"
    MockClient.return_value.set.assert_called_once_with("1.3.6.1.2.1.2.2.1.7.1", "2", "int")


@pytest.mark.asyncio
async def test_snmp_set_sem_permissao_devices_snmp_set_da_403(db_session):
    from fastapi import HTTPException

    asset, _profile, command, claims = await _seed_device(
        db_session, is_real=True, allow_real_snmp_set=True, **_set_kwargs(),
    )
    with pytest.raises(HTTPException) as exc_info:
        await execute_device_command(str(asset.id), str(command.id), claims, db_session, ExecuteCommandIn(value="2"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_snmp_set_sem_valor_vira_status_error(db_session):
    asset, _profile, command, claims = await _seed_device(
        db_session, is_real=True, allow_real_snmp_set=True, extra_perms=("devices.snmp.set",), **_set_kwargs(),
    )
    result = await execute_device_command(str(asset.id), str(command.id), claims, db_session)
    assert result.status == "error"
    assert "valor" in result.output
