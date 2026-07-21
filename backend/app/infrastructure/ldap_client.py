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


    # ------------------------------------------------------------------
    # Fase 9c - Gestao de OUs (Organizational Units)
    # ------------------------------------------------------------------
    def list_ous(self, base_dn: str | None = None) -> list[dict]:
        """Lista as OUs a partir de base_dn (ou de settings.ad_root_ou, se nao informado)."""
        base = base_dn or settings.ad_root_ou
        with self._conn() as c:
            c.search(base, "(objectClass=organizationalUnit)", SUBTREE,
                      attributes=["ou", "distinguishedName"])
            out = []
            for e in c.entries:
                dn = str(e.distinguishedName)
                parent_dn = dn.split(",", 1)[1] if "," in dn else ""
                out.append({"name": str(e.ou), "dn": dn, "parent_dn": parent_dn})
            return out

    def create_ou(self, name: str, parent_dn: str | None = None) -> str:
        """Cria uma OU nova sob parent_dn (ou sob settings.ad_root_ou, se nao informado)."""
        parent = parent_dn or settings.ad_root_ou
        dn = f"OU={name},{parent}"
        with self._conn() as c:
            c.add(dn, ["top", "organizationalUnit"], {"ou": name})
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao criar OU '{name}': {c.result.get('description')}")
        return dn

    def rename_ou(self, dn: str, new_name: str) -> str:
        """Renomeia a OU (troca o RDN, mantendo o mesmo pai)."""
        new_rdn = f"OU={new_name}"
        with self._conn() as c:
            c.modify_dn(dn, new_rdn)
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao renomear OU: {c.result.get('description')}")
        parent = dn.split(",", 1)[1]
        return f"{new_rdn},{parent}"

    def move_ou(self, dn: str, new_parent_dn: str) -> str:
        """Move a OU para debaixo de um novo pai (mantendo o mesmo nome)."""
        rdn = dn.split(",", 1)[0]
        with self._conn() as c:
            c.modify_dn(dn, rdn, new_superior=new_parent_dn)
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao mover OU: {c.result.get('description')}")
        return f"{rdn},{new_parent_dn}"

    def _ou_has_children(self, c: Connection, dn: str) -> bool:
        c.search(dn, "(objectClass=*)", SUBTREE, attributes=["distinguishedName"], size_limit=2)
        # a propria OU aparece como 1 resultado; mais que isso indica filhos
        return len(c.entries) > 1

    def delete_ou(self, dn: str) -> None:
        """Exclui a OU, com validacao de que ela esta vazia antes."""
        with self._conn() as c:
            if self._ou_has_children(c, dn):
                raise ValueError(
                    "OU nao esta vazia; mova ou remova os objetos filhos antes de excluir."
                )
            c.delete(dn)
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao excluir OU: {c.result.get('description')}")


    # ------------------------------------------------------------------
    # Fase 9c - Gestao de Grupos
    # ------------------------------------------------------------------
    _GROUP_SCOPE_BITS = {"Global": 0x2, "DomainLocal": 0x4, "Universal": 0x8}
    _GROUP_SECURITY_BIT = 0x80000000

    def _group_type_value(self, scope: str, group_type: str) -> int:
        if scope not in self._GROUP_SCOPE_BITS:
            raise ValueError(f"scope invalido: {scope!r} (use Global, DomainLocal ou Universal)")
        if group_type not in ("Security", "Distribution"):
            raise ValueError(f"group_type invalido: {group_type!r} (use Security ou Distribution)")
        value = self._GROUP_SCOPE_BITS[scope]
        if group_type == "Security":
            value |= self._GROUP_SECURITY_BIT
            value -= 2**32  # AD guarda groupType como inteiro assinado de 32 bits
        return value

    def _parse_group_type(self, raw: int) -> tuple[str, str]:
        value = raw if raw >= 0 else raw + 2**32
        group_type = "Security" if (value & self._GROUP_SECURITY_BIT) else "Distribution"
        scope_bits = value & 0x0F
        scope = next((s for s, b in self._GROUP_SCOPE_BITS.items() if b == scope_bits), "Global")
        return scope, group_type

    def list_groups(self, base_dn: str | None = None) -> list[dict]:
        base = base_dn or settings.ad_root_ou
        with self._conn() as c:
            c.search(base, "(objectClass=group)", SUBTREE,
                      attributes=["cn", "distinguishedName", "description", "groupType", "member"])
            out = []
            for e in c.entries:
                scope, group_type = self._parse_group_type(int(e.groupType.value))
                out.append({
                    "name": str(e.cn),
                    "dn": str(e.distinguishedName),
                    "description": str(e.description) if e.description.value else "",
                    "scope": scope,
                    "group_type": group_type,
                    "member_count": len(e.member.values or []),
                })
            return out

    def create_group(
        self, name: str, parent_dn: str | None = None,
        scope: str = "Global", group_type: str = "Security", description: str = "",
    ) -> str:
        parent = parent_dn or settings.ad_root_ou
        dn = f"CN={name},{parent}"
        gtype_value = self._group_type_value(scope, group_type)
        attrs = {
            "sAMAccountName": name,
            "groupType": gtype_value,
        }
        if description:
            attrs["description"] = description
        with self._conn() as c:
            c.add(dn, ["top", "group"], attrs)
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao criar grupo '{name}': {c.result.get('description')}")
        return dn

    def rename_group(self, dn: str, new_name: str) -> str:
        new_rdn = f"CN={new_name}"
        with self._conn() as c:
            c.modify_dn(dn, new_rdn)
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao renomear grupo: {c.result.get('description')}")
            c.modify(f"{new_rdn},{dn.split(',', 1)[1]}", {"sAMAccountName": [(MODIFY_REPLACE, [new_name])]})
        parent = dn.split(",", 1)[1]
        return f"{new_rdn},{parent}"

    def update_group(
        self, dn: str, description: str | None = None,
        scope: str | None = None, group_type: str | None = None,
    ) -> None:
        with self._conn() as c:
            changes = {}
            if description is not None:
                changes["description"] = [(MODIFY_REPLACE, [description])]
            if scope is not None or group_type is not None:
                c.search(dn, "(objectClass=group)", attributes=["groupType"])
                if not c.entries:
                    raise LookupError(f"Grupo '{dn}' nao encontrado")
                cur_scope, cur_type = self._parse_group_type(int(c.entries[0].groupType.value))
                new_value = self._group_type_value(scope or cur_scope, group_type or cur_type)
                changes["groupType"] = [(MODIFY_REPLACE, [new_value])]
            if changes:
                c.modify(dn, changes)
                if not c.result.get("result") == 0:
                    raise RuntimeError(f"Falha ao atualizar grupo: {c.result.get('description')}")

    def delete_group(self, dn: str) -> None:
        with self._conn() as c:
            c.delete(dn)
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao excluir grupo: {c.result.get('description')}")


    # ------------------------------------------------------------------
    # Fase 9c - Gestao de Computadores
    # ------------------------------------------------------------------
    def list_computers(self, base_dn: str | None = None) -> list[dict]:
        base = base_dn or settings.ad_root_ou
        with self._conn() as c:
            c.search(base, "(objectClass=computer)", SUBTREE,
                      attributes=["cn", "distinguishedName", "operatingSystem", "userAccountControl"])
            out = []
            for e in c.entries:
                uac = int(e.userAccountControl.value or 0)
                out.append({
                    "name": str(e.cn),
                    "dn": str(e.distinguishedName),
                    "os": str(e.operatingSystem) if e.operatingSystem.value else "",
                    "disabled": bool(uac & UAC_ACCOUNTDISABLE),
                })
            return out

    def set_computer_enabled(self, dn: str, enabled: bool) -> None:
        with self._conn() as c:
            c.search(dn, "(objectClass=computer)", attributes=["userAccountControl"])
            if not c.entries:
                raise LookupError(f"Computador '{dn}' nao encontrado")
            uac = int(c.entries[0].userAccountControl.value)
            uac = (uac & ~UAC_ACCOUNTDISABLE) if enabled else (uac | UAC_ACCOUNTDISABLE)
            c.modify(dn, {"userAccountControl": [(MODIFY_REPLACE, [uac])]})
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao alterar status do computador: {c.result.get('description')}")

    def move_computer(self, dn: str, new_parent_dn: str) -> str:
        rdn = dn.split(",", 1)[0]
        with self._conn() as c:
            c.modify_dn(dn, rdn, new_superior=new_parent_dn)
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao mover computador: {c.result.get('description')}")
        return f"{rdn},{new_parent_dn}"

    def delete_computer(self, dn: str) -> None:
        with self._conn() as c:
            c.delete(dn)
            if not c.result.get("result") == 0:
                raise RuntimeError(f"Falha ao excluir computador: {c.result.get('description')}")
