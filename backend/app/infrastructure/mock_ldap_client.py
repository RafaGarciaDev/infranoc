"""
Cliente LDAP mock, usado quando settings.ad_mock=True (ex.: deploy de demo publica).

Gera dados sinteticos de usuarios (mesmo formato do LdapClient real), sem
nenhuma conexao com o Active Directory real. Usado para nao expor a VM de
laboratorio (DC01) em ambientes publicos.
"""
import random

_DEPARTAMENTOS = [
    "Producao", "TI", "RH", "Financeiro",
    "Comercial", "Manutencao", "Qualidade", "Logistica",
]

_CARGOS = {
    "Producao": ["Operador de Pasteurizacao", "Operador de Producao", "Supervisor de Linha"],
    "TI": ["Analista de Suporte", "Administrador de Redes", "Analista de Sistemas"],
    "RH": ["Analista de RH", "Assistente de RH", "Coordenador de RH"],
    "Financeiro": ["Analista Financeiro", "Assistente Financeiro", "Controller"],
    "Comercial": ["Vendedor", "Representante Comercial", "Gerente Comercial"],
    "Manutencao": ["Tecnico de Manutencao", "Eletricista Industrial", "Supervisor de Manutencao"],
    "Qualidade": ["Analista de Qualidade", "Inspetor de Qualidade", "Coordenador de Qualidade"],
    "Logistica": ["Assistente de Logistica", "Conferente", "Coordenador de Logistica"],
}

_NOMES = [
    "Julia", "Alexandre", "Silvia", "Ricardo", "Simone", "Marcelo", "Patricia",
    "Fernando", "Camila", "Rodrigo", "Aline", "Bruno", "Larissa", "Diego",
    "Vanessa", "Thiago", "Renata", "Gustavo", "Priscila", "Leonardo", "Bianca",
    "Rafael", "Mariana", "Eduardo", "Fernanda", "Vinicius", "Carla", "Anderson",
    "Juliana", "Felipe",
]
_SOBRENOMES = [
    "Moreira Gomes", "Fernandes Pereira", "Marques Freitas", "Martins Rocha",
    "Rocha Silva", "Souza Lima", "Oliveira Santos", "Costa Almeida",
    "Ribeiro Barbosa", "Carvalho Nunes", "Araujo Correia", "Teixeira Dias",
    "Cardoso Vieira", "Pinto Cavalcanti", "Monteiro Azevedo",
]


def _gerar_usuarios(total: int = 250, seed: int = 7) -> list[dict]:
    rnd = random.Random(seed)
    usuarios = []
    for i in range(total):
        nome = rnd.choice(_NOMES)
        sobrenome = rnd.choice(_SOBRENOMES)
        display_name = f"{nome} {sobrenome}"
        sam = f"{nome.lower()}.{sobrenome.split()[0].lower()}{i}"
        dept = _DEPARTAMENTOS[i % len(_DEPARTAMENTOS)]
        cargo = rnd.choice(_CARGOS[dept])
        disabled = rnd.random() < 0.01
        locked = (not disabled) and rnd.random() < 0.005
        usuarios.append(
            {
                "sam": sam,
                "display_name": display_name,
                "email": f"{sam}@infranoc.lab",
                "title": cargo,
                "department": dept,
                "disabled": disabled,
                "locked": locked,
                "dn": f"CN={display_name},OU={dept},OU=Usuarios,OU=VALEVERDE,DC=infranoc,DC=lab",
                "groups": [dept],
            }
        )
    return usuarios


class MockLdapClient:
    """Substituto do LdapClient real para ambientes de demo publica (sem AD de verdade)."""

    def __init__(self):
        self._usuarios = _gerar_usuarios()

    def search_users(self, q: str | None = None, ou: str | None = None, limit: int = 200) -> list[dict]:
        rows = self._usuarios
        if q:
            ql = q.lower()
            rows = [
                u for u in rows
                if ql in u["sam"].lower() or ql in u["display_name"].lower() or ql in u["email"].lower()
            ]
        return rows[:limit]

    def set_enabled(self, sam: str, enabled: bool) -> None:
        raise RuntimeError("Modo demo: escrita no AD desabilitada (ad.write nao concedido ao papel Demo).")

    def set_group(self, sam: str, group_dn: str, add: bool) -> None:
        raise RuntimeError("Modo demo: escrita no AD desabilitada (ad.write nao concedido ao papel Demo).")

    def create_user(self, sam: str, display_name: str, given: str, surname: str, ou: str, title: str = "", dept: str = "") -> str:
        raise RuntimeError("Modo demo: escrita no AD desabilitada (ad.write nao concedido ao papel Demo).")
