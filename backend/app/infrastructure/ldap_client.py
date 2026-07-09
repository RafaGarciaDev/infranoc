"""
Cliente LDAP para o modulo Active Directory (Fase 5).

Responsavel por leitura e escrita direta via LDAP (ldap3):
- busca de usuarios (com filtro por texto e OU)
- habilitar/desabilitar conta (bit userAccountControl)
- adicionar/remover usuario de grupo
- criar usuario (fica desabilitado ate ter senha definida via PsAdOps)

Reset de senha e desbloqueio ficam em app/infrastructure/ps_ad_ops.py (PowerShell Remoting),
pois o AD exige conexao segura (LDAPS) para operacoes de senha via LDAP puro.
"""
import logging

from ldap3 import ALL, MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE, SUBTREE, Connection, Server

from app.core.config import settings

logger = logging.getLogger(__name__)

# Bit de userAccountControl que indica conta desabilitada (0x2 = ACCOUNTDISABLE)
UAC_ACCOUNTDISABLE = 0x2


class LdapClient:
    """Cliente fino sobre ldap3, escopado a OU de usuarios do dominio infranoc.lab."""

    def __init__(self):
        self.server = Server(
            settings.ad_server,
            port=settings.ad_port,
            use_ssl=settings.ad_use_ssl,
            get_info=ALL,
        )
        self.base = settings.ad_users_ou

    def _conn(self) -> Connection:
        # Nunca logar settings.ad_bind_password, nem em caso de erro de bind.
        return Connection(
            self.server,
            user=settings.ad_bind_user,
            password=settings.ad_bind_password,
            auto_bind=True,
        )

    def search_users(
        self, q: str | None = None, ou: str | None = None, limit: int = 200
    ) -> list[dict]:
        """Busca usuarios na OU configurada (ou outra, se informada), com filtro livre opcional."""
        flt = "(&(objectCategory=person)(objectClass=user)"
        if q:
            flt += f"(|(sAMAccountName=*{q}*)(displayName=*{q}*)(mail=*{q}*))"
        flt += ")"

        attrs = [
            "sAMAccountName",
            "displayName",
            "mail",
            "title",
            "department",
            "userAccountControl",
            "lockoutTime",
            "memberOf",
            "distinguishedName",
        ]

        logger.info("Buscando usuarios AD (q=%r, ou=%r, limit=%d)", q, ou, limit)

        with self._conn() as c:
            c.search(ou or self.base, flt, SUBTREE, attributes=attrs, size_limit=limit)
            out = []
            for e in c.entries:
                uac = int(e.userAccountControl.value or 0)
                locked = bool(e.lockoutTime.value) and str(e.lockoutTime.value) not in (
                    "0",
                    "1601-01-01 00:00:00+00:00",
                )
                out.append(
                    {
                        "sam": str(e.sAMAccountName),
                        "display_name": str(e.displayName),
                        "email": str(e.mail),
                        "title": str(e.title),
                        "department": str(e.department),
                        "disabled": bool(uac & UAC_ACCOUNTDISABLE),
                        "locked": locked,
                        "dn": str(e.distinguishedName),
                        "groups": [
                            dn.split(",")[0].replace("CN=", "")
                            for dn in (e.memberOf.values or [])
                        ],
                    }
                )
        logger.info("Busca retornou %d usuario(s)", len(out))
        return out

    def _dn_of(self, c: Connection, sam: str) -> str:
        c.search(self.base, f"(sAMAccountName={sam})", attributes=["distinguishedName"])
        if not c.entries:
            raise LookupError(f"Usuario '{sam}' nao encontrado no AD")
        return str(c.entries[0].distinguishedName)

    def set_enabled(self, sam: str, enabled: bool) -> None:
        """Habilita ou desabilita a conta via bit userAccountControl."""
        logger.info("Alterando enabled=%s para usuario sam=%s", enabled, sam)
        with self._conn() as c:
            c.search(
                self.base,
                f"(sAMAccountName={sam})",
                attributes=["userAccountControl", "distinguishedName"],
            )
            if not c.entries:
                raise LookupError(f"Usuario '{sam}' nao encontrado no AD")
            e = c.entries[0]
            uac = int(e.userAccountControl.value)
            uac = (uac & ~UAC_ACCOUNTDISABLE) if enabled else (uac | UAC_ACCOUNTDISABLE)
            c.modify(str(e.distinguishedName), {"userAccountControl": [(MODIFY_REPLACE, [uac])]})
            if not c.result.get("result") == 0:
                logger.error("Falha ao alterar userAccountControl de %s: %s", sam, c.result)
                raise RuntimeError(f"Falha ao alterar status de '{sam}': {c.result.get('description')}")

    def set_group(self, sam: str, group_dn: str, add: bool) -> None:
        """Adiciona ou remove o usuario de um grupo (member attribute do grupo)."""
        action = "Adicionando" if add else "Removendo"
        logger.info("%s sam=%s ao/do grupo=%s", action, sam, group_dn)
        with self._conn() as c:
            user_dn = self._dn_of(c, sam)
            modify_op = MODIFY_ADD if add else MODIFY_DELETE
            c.modify(group_dn, {"member": [(modify_op, [user_dn])]})
            if not c.result.get("result") == 0:
                logger.error("Falha ao alterar membership de %s em %s: %s", sam, group_dn, c.result)
                raise RuntimeError(
                    f"Falha ao alterar grupo de '{sam}': {c.result.get('description')}"
                )

    def create_user(
        self,
        sam: str,
        display_name: str,
        given: str,
        surname: str,
        ou: str,
        title: str = "",
        dept: str = "",
    ) -> str:
        """Cria o usuario no AD. Fica desabilitado (UAC=514) ate ter senha definida via PsAdOps."""
        dn = f"CN={display_name},OU={ou},OU=Usuarios,OU=VALEVERDE,DC=infranoc,DC=lab"
        logger.info("Criando usuario AD sam=%s dn=%s", sam, dn)
        with self._conn() as c:
            c.add(
                dn,
                ["top", "person", "organizationalPerson", "user"],
                {
                    "sAMAccountName": sam,
                    "userPrincipalName": f"{sam}@infranoc.lab",
                    "displayName": display_name,
                    "givenName": given,
                    "sn": surname,
                    "title": title,
                    "department": dept,
                    "userAccountControl": 514,  # desabilitado ate ter senha (ver ps_ad_ops.reset_password)
                },
            )
            if not c.result.get("result") == 0:
                logger.error("Falha ao criar usuario %s: %s", sam, c.result)
                raise RuntimeError(f"Falha ao criar usuario '{sam}': {c.result.get('description')}")
        return dn