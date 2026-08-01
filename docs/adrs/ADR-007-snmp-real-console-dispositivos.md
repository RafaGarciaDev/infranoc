# ADR-007: SNMP real (GET+SET) no Console de Gestao de Dispositivos

## Status
Aceito

## Contexto
O ADR-006 ja registrava como pendencia futura: "instalar agentes SNMP reais
na DC01/MES01, expandir o catalogo de comandos, desenhar a etapa de revisao
para liberar comandos de acao reais". O dono do projeto quer avancar essa
pendencia: transformar o Console de Dispositivos (9L) num painel abrangente
de manutencao para ativos de rede/cyber (switches, routers, firewalls, APs,
impressoras, UPS), com execucao SNMP real de verdade (GET e SET), nativo
dentro do InfraNOC - sem trazer ferramentas externas (Rundeck/GLPI/Zabbix).

Confirmado com o usuario: (a) quer GET e SET reais, aceitando o risco de SET
em hardware real; (b) nao ha nenhum hardware SNMP real disponivel no
laboratorio hoje - a implementacao fica pronta para quando um dispositivo de
verdade for plugado, seguindo o mesmo padrao ja usado pra SSH/WinRM (real
so quando `is_real=True`, resto simulado); (c) para o SET real, quer uma
trava dupla de seguranca - nao basta uma unica flag ou permissao.

## Decisao

### GET SNMP real - sem trava adicional alem de `is_real`
Generalizamos o dispatcher de execucao real: antes, so o comando
`get_status` tinha execucao real (SSH/WinRM, so nos 2 ativos reais). Agora,
**qualquer comando de leitura (`kind=Read`) com um `oid` cadastrado no
catalogo (`DeviceCommand.oid`) roda de verdade via SNMP quando o perfil do
ativo e `is_real=True`** - mesma postura de risco ja aprovada e validada em
producao no ADR-006 para o GET de SSH/WinRM (leitura nao e destrutiva).
SSH/WinRM continuam exatamente como estavam, restritos a `get_status` -
nenhuma mudanca de comportamento pra esses dois protocolos.

O host do SNMP vem do `Asset.ip_address` de cada ativo (nao ha host fixo em
`settings`, diferente de SSH/WinRM que sempre miram DC01/MES01), porque o
objetivo e cobrir varios dispositivos de rede, nao 2 hosts fixos.

### SET SNMP real - trava dupla, unica excecao ao ADR-006
O ADR-006 bloqueou deliberadamente toda **acao** real (`kind=Action`, ex:
`restart_service`) por falta de uma "etapa de revisao" madura - continua
valendo integralmente para SSH/WinRM e para a maioria dos comandos SNMP
(ex: `restart` de reboot total, que nem tem OID cadastrado - nao existe OID
padrao seguro de reboot no IF-MIB, permanece sempre simulado).

A unica excecao e SNMP SET quando **3 condicoes simultaneas** sao
satisfeitas:
1. `DeviceProtocolProfile.is_real = True` (ativo e real).
2. `DeviceProtocolProfile.allow_real_snmp_set = True` - **opt-in explicito
   por ativo**, default `False` mesmo quando `is_real=True`. Marcar um
   ativo como real (pra habilitar GET) nunca libera SET automaticamente.
3. O operador tem a permissao `devices.snmp.set` - **opt-in explicito por
   role/operador**, alem da `devices.action` ja exigida pelo comando.

Essa dupla trava (por-ativo + por-operador) e a "etapa de revisao minima
viavel" que o ADR-006 dizia faltar: dois opt-ins deliberados e separados,
em vez de uma unica flag/permissao que relaxaria a postura de seguranca de
forma ampla demais (ex: o dia que um 3o ativo virar `is_real=True` pra
testar GET, SET destrutivo ja estaria liberado por padrao pra quem tiver
`devices.action`).

O unico comando de Acao com OID cadastrado no catalogo curado e
`set_port_admin_status` (switch, `ifAdminStatus` do IF-MIB - liga/desliga
1 porta, nao o equipamento inteiro). Foi escolhido deliberadamente por ser
o caso mais seguro/realista de SET: escopo limitado a uma unica porta, sem
"OID de reboot total" universal e seguro.

### Onde fica o OID
`DeviceCommand` ganhou os campos `oid: str | None` e `value_type: str | None`
(`"string"|"int"|"gauge"|"unsigned"`), preenchidos pelo `seed_devices.py`.
Alternativa descartada: guardar o OID num dict Python solto (como o `fakes`
de `_run_simulated`) - criaria uma segunda fonte de verdade que pode
divergir do catalogo. Ficam `None` para SSH/WinRM/HTTPAPI/Modbus (sem
mudanca de postura pra esses protocolos) e para comandos sem execucao real
disponivel (ex: `restart` de reboot total).

## Consequencias
- Ativos de rede/cyber (NetworkSwitch, Router, Firewall, AccessPoint,
  Printer, UPS) ganham comandos de leitura reais quando `is_real=True`:
  status/uptime/interface (IF-MIB, `sysUpTime`/`ifOperStatus`), toner/
  contador de paginas de impressora (Printer-MIB, RFC 3805), bateria/carga/
  autonomia de UPS (UPS-MIB, RFC 1628).
- Hoje **nenhum ativo do CMDB tem `DeviceProtocolProfile.protocol=SNMP` com
  `is_real=True`** - o comportamento visivel no console nao muda ate o
  usuario plugar um dispositivo SNMP real e marcar seu perfil manualmente
  (mesma logica ja usada pra SSH/WinRM desde o ADR-006).
- Primeiro SNMP SET real so ocorre quando **as 3 condicoes da trava dupla**
  forem satisfeitas ao mesmo tempo - nenhuma combinacao de dado seedado
  hoje libera isso "sem querer" (`allow_real_snmp_set` nasce `False`,
  `devices.snmp.set` nao e concedida a nenhuma role por padrao alem do
  papel Admin, que ja tem todas as permissoes do sistema).
- SSH/WinRM Action e a maioria dos comandos SNMP Action (ex: `restart`)
  continuam 100% simulados - o ADR-006 permanece valido pra eles.
- Ao instalar o primeiro dispositivo SNMP real, alem de marcar
  `is_real=True`, e necessario preencher `Asset.ip_address` (hoje so os 2
  ativos reais do lab tem esse campo populado) - sem IP, o GET/SET real
  falha com erro claro (`status=error`) em vez de silenciosamente cair pro
  simulado.
