# ADR-006: Console de Gestao de Dispositivos com dados majoritariamente simulados

## Status
Aceito

## Contexto
A Fase 9L pede um console unificado que fale com os ativos de rede via
protocolos apropriados (SNMP, SSH, WinRM, HTTP/API, Modbus), no estilo de
um NMS (Network Management System - Zabbix/PRTG/SolarWinds), permitindo
monitorar e executar comandos direto do InfraNOC.

## Decisao
Dos 646 ativos do CMDB, apenas 2 sao reais: `PSA-TI-DC01` (Windows Server,
AD) e `PSA-OT-MES01` (Linux). Os demais (~644: impressoras, switches,
camaras, CLPs, nobreaks) sao simulados por containers Python que so
expoem metricas Prometheus (Fase 3) - nao existem fisicamente, nao tem
agente SNMP real, nao aceitam SSH.

Nao rodamos protocolos reais (SNMP/SSH/WinRM/HTTP/Modbus) contra esses
ativos simulados. Os motivos:
1. **Nao ha nada real do outro lado**: um "switch" simulado e uma linha
   de codigo Python gerando numeros aleatorios, nao um dispositivo com
   IP/porta de gestao reais.
2. **O objetivo da sub-fase e o console e a logica de negocio**: navegar
   por ativo, ver comandos disponiveis, executar, auditar - nao operar
   protocolos de gestao de rede de fato em cada tipo de equipamento.
3. **Mesma filosofia dos ADR-003 (Backup), ADR-004 (SIEM) e ADR-005
   (VPN)**: simular a fonte de dados, manter real a modelagem e a logica
   de consulta/execucao.

Optamos por:
- Modelar `DeviceProtocolProfile` como entidade de primeira classe,
  vinculando cada ativo do CMDB a um protocolo (`ssh`, `winrm`, `snmp`,
  `http_api`, `modbus`) e uma porta padrao, com uma flag `is_real`
  marcando exclusivamente os 2 ativos verdadeiros do lab.
- Modelar `DeviceCommand` como um catalogo curado (16 comandos iniciais,
  cobrindo os tipos de ativo mais representativos), nao uma lista
  exaustiva de "todos os comandos possiveis" de todo fabricante - mesma
  abordagem das 12 regras curadas do ADR-004.
- Modelar `DeviceCommandExecution` como log de auditoria dedicado (status
  `success`/`error`/`simulated`, saida, quem executou), alem do
  `audit_log` geral do sistema.
- **Para os 2 ativos reais, o comando `get_status` e genuinamente real**:
  reaproveita o `SshClient` (asyncssh) ja usado no Linux Ops (Fase 9d)
  para a `MES01`, e uma conexao WinRM (pypsrp) com as credenciais da
  conta de servico `svc_infranoc` (Fase 5) para a `DC01`. Validado em
  producao no lab: `get_status` retornou o `uptime` real da `MES01` via
  SSH e a data/hostname reais da `DC01` via WinRM.
- **Comandos de acao (`kind="action"`, ex.: `restart_service`)
  permanecem simulados mesmo nos 2 ativos reais**, nesta primeira
  versao - decisao deliberada de seguranca. Nao ha ainda uma etapa de
  confirmacao/revisao robusta o suficiente para autorizar uma acao
  potencialmente disruptiva (reiniciar servico, etc.) contra a infra
  real do laboratorio a partir de um clique no console.
- Cada execucao verifica a permissao especifica do comando
  (`requires_permission`, ex.: `devices.read` ou `devices.action`) contra
  as permissoes do token JWT, alem da permissao geral `devices.read` para
  acessar o modulo.

### Lacuna descoberta e corrigida durante a implementacao
Ao modelar `DeviceProtocolProfile` (que exige um `asset_id` valido),
descobrimos que `PSA-TI-DC01` e `PSA-OT-MES01` **nunca haviam sido
cadastrados como `Asset` no CMDB** - existiam apenas como alvos de scrape
do Prometheus (`windows_exporter`/`node_exporter`, Fase 3) e como strings
soltas em `seed_backup.py`/`seed_security.py`. Essa e uma lacuna
pre-existente de fases anteriores, nao introduzida pela 9L. Foi corrigida
com um seed dedicado (`seed_real_assets.py`) que cria os dois ativos no
CMDB antes de gerar os perfis de protocolo.

## Consequencias
- O console reflete uma arquitetura de dados, uma logica de execucao e
  uma auditoria dedicada prontas para uso real, mas a esmagadora maioria
  dos "comandos" e "dispositivos" e fabricada, nao coletada de protocolos
  de gestao reais.
- Isso deve ficar claro em qualquer demonstracao do projeto, para nao
  passar a impressao de que ha um NMS real operando 644 dispositivos.
- Comandos de acao sobre os 2 ativos reais continuam simulados ate que
  uma etapa de confirmacao/revisao adequada seja desenhada - registrar
  como pendencia explicita antes de habilitar acao real em qualquer
  ativo do lab.
- Ao migrar para o servidor dedicado (Fase 9a), avaliar: (a) instalar
  agentes SNMP reais na `DC01`/`MES01` para tornar tambem esse protocolo
  genuino nos 2 ativos reais; (b) expandir o catalogo de comandos alem
  dos 16 iniciais; (c) desenhar a etapa de revisao para liberar comandos
  de acao reais.
- `PSA-TI-DC01` e `PSA-OT-MES01` agora existem como `Asset` de verdade no
  CMDB (setor "Ti Datacenter") - outras fases que hoje referenciam esses
  nomes como string solta (backup, SIEM) poderiam, no futuro, migrar para
  referenciar o `asset_id` real em vez do nome.
