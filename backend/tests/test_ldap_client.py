"""Testes unitarios do LdapClient (Fase 5 - Active Directory).

Nao depende de banco nem de LDAP real: o ldap3.Connection e mockado,
entao roda em qualquer ambiente sem precisar de testcontainers ou da DC01.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.ldap_client import UAC_ACCOUNTDISABLE, LdapClient


class _FakeAttr:
    """Simula um atributo ldap3 (que expoe .value e, para multi-valor, .values)."""

    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values if values is not None else ([] if value is None else [value])

    def __str__(self):
        return str(self.value) if self.value is not None else ""


class _FakeEntry:
    """Simula uma entrada (Entry) retornada por ldap3 apos c.search(...)."""

    def __init__(self, **attrs):
        for name, value in attrs.items():
            setattr(self, name, _FakeAttr(value=value))


def _make_fake_connection(entries):
    """Cria um mock de Connection que suporta 'with self._conn() as c: ...'."""
    conn = MagicMock()
    conn.entries = entries
    conn.result = {"result": 0, "description": "success"}
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


@pytest.fixture
def client():
    with patch("app.infrastructure.ldap_client.Server"):
        return LdapClient()


class TestSearchUsersQuery:
    """Confere que search_users monta o filtro LDAP correto."""

    def test_monta_filtro_sem_texto_livre(self, client):
        fake_conn = _make_fake_connection(entries=[])
        with patch.object(client, "_conn", return_value=fake_conn):
            client.search_users()

        called_filter = fake_conn.search.call_args.args[1]
        assert called_filter == "(&(objectCategory=person)(objectClass=user))"

    def test_monta_filtro_com_texto_livre(self, client):
        fake_conn = _make_fake_connection(entries=[])
        with patch.object(client, "_conn", return_value=fake_conn):
            client.search_users(q="silva")

        called_filter = fake_conn.search.call_args.args[1]
        assert "sAMAccountName=*silva*" in called_filter
        assert "displayName=*silva*" in called_filter
        assert "mail=*silva*" in called_filter

    def test_usa_ou_customizada_quando_informada(self, client):
        fake_conn = _make_fake_connection(entries=[])
        custom_ou = "OU=TI,OU=VALEVERDE,DC=infranoc,DC=lab"
        with patch.object(client, "_conn", return_value=fake_conn):
            client.search_users(ou=custom_ou)

        called_base = fake_conn.search.call_args.args[0]
        assert called_base == custom_ou

    def test_usa_base_padrao_quando_ou_nao_informada(self, client):
        fake_conn = _make_fake_connection(entries=[])
        with patch.object(client, "_conn", return_value=fake_conn):
            client.search_users()

        called_base = fake_conn.search.call_args.args[0]
        assert called_base == client.base

    def test_respeita_size_limit(self, client):
        fake_conn = _make_fake_connection(entries=[])
        with patch.object(client, "_conn", return_value=fake_conn):
            client.search_users(limit=42)

        assert fake_conn.search.call_args.kwargs["size_limit"] == 42


class TestSearchUsersParsing:
    """Confere que search_users parseia userAccountControl e lockoutTime corretamente."""

    def _fake_user_entry(self, uac: int, locked=False, groups=None):
        return _FakeEntry(
            sAMAccountName="jsilva",
            displayName="Joao Silva",
            mail="jsilva@infranoc.lab",
            title="Analista",
            department="TI",
            userAccountControl=uac,
            lockoutTime="132500000000000000" if locked else "0",
            memberOf=None,
            distinguishedName="CN=Joao Silva,OU=TI,OU=Usuarios,OU=VALEVERDE,DC=infranoc,DC=lab",
            lastLogonTimestamp=None,
        )

    def test_conta_habilitada_nao_marca_disabled(self, client):
        entry = self._fake_user_entry(uac=512)  # 512 = NORMAL_ACCOUNT, sem o bit 0x2
        fake_conn = _make_fake_connection(entries=[entry])
        with patch.object(client, "_conn", return_value=fake_conn):
            result = client.search_users()

        assert result[0]["disabled"] is False

    def test_conta_desabilitada_marca_disabled(self, client):
        entry = self._fake_user_entry(uac=512 | UAC_ACCOUNTDISABLE)  # 514
        fake_conn = _make_fake_connection(entries=[entry])
        with patch.object(client, "_conn", return_value=fake_conn):
            result = client.search_users()

        assert result[0]["disabled"] is True

    def test_conta_bloqueada_marca_locked(self, client):
        entry = self._fake_user_entry(uac=512, locked=True)
        fake_conn = _make_fake_connection(entries=[entry])
        with patch.object(client, "_conn", return_value=fake_conn):
            result = client.search_users()

        assert result[0]["locked"] is True

    def test_conta_nao_bloqueada_nao_marca_locked(self, client):
        entry = self._fake_user_entry(uac=512, locked=False)
        fake_conn = _make_fake_connection(entries=[entry])
        with patch.object(client, "_conn", return_value=fake_conn):
            result = client.search_users()

        assert result[0]["locked"] is False

    def test_campos_basicos_sao_mapeados(self, client):
        entry = self._fake_user_entry(uac=512)
        fake_conn = _make_fake_connection(entries=[entry])
        with patch.object(client, "_conn", return_value=fake_conn):
            result = client.search_users()

        assert result[0]["sam"] == "jsilva"
        assert result[0]["display_name"] == "Joao Silva"
        assert result[0]["email"] == "jsilva@infranoc.lab"
        assert result[0]["department"] == "TI"


class TestSetEnabled:
    """Confere que set_enabled liga/desliga o bit correto sem mexer nos demais bits."""

    def test_desabilitar_liga_o_bit(self, client):
        entry = _FakeEntry(
            userAccountControl=512,
            distinguishedName="CN=Joao Silva,OU=TI,OU=Usuarios,OU=VALEVERDE,DC=infranoc,DC=lab",
        )
        fake_conn = _make_fake_connection(entries=[entry])
        with patch.object(client, "_conn", return_value=fake_conn):
            client.set_enabled("jsilva", enabled=False)

        modify_call = fake_conn.modify.call_args
        new_uac = modify_call.args[1]["userAccountControl"][0][1][0]
        assert new_uac & UAC_ACCOUNTDISABLE

    def test_habilitar_desliga_o_bit(self, client):
        entry = _FakeEntry(
            userAccountControl=512 | UAC_ACCOUNTDISABLE,
            distinguishedName="CN=Joao Silva,OU=TI,OU=Usuarios,OU=VALEVERDE,DC=infranoc,DC=lab",
        )
        fake_conn = _make_fake_connection(entries=[entry])
        with patch.object(client, "_conn", return_value=fake_conn):
            client.set_enabled("jsilva", enabled=True)

        modify_call = fake_conn.modify.call_args
        new_uac = modify_call.args[1]["userAccountControl"][0][1][0]
        assert not (new_uac & UAC_ACCOUNTDISABLE)

    def test_usuario_inexistente_levanta_erro(self, client):
        fake_conn = _make_fake_connection(entries=[])
        with patch.object(client, "_conn", return_value=fake_conn):
            with pytest.raises(LookupError):
                client.set_enabled("naoexiste", enabled=True)