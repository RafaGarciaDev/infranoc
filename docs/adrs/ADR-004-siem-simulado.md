# ADR-004: Painel de Seguranca com dados simulados (sem Wazuh real no lab)

## Status
Aceito

## Contexto

A Fase 9g pede um painel de SIEM (Security Information and Event Management)
mostrando eventos de seguranca, correlacao e mapeamento para o framework
MITRE ATT&CK. A ferramenta open-source de referencia para isso e o Wazuh.

## Decisao

Nao rodamos uma instancia real do Wazuh no laboratorio. Os motivos:

1. **Custo de RAM desproporcional**: o stack completo do Wazuh (Manager +
   Indexer, que e um fork do OpenSearch + Dashboard) consome ~5GB de RAM,
   o que nao cabe confortavelmente junto aos 14+ containers ja rodando no
   ambiente de 16GB de RAM compartilhado com o restante do trabalho.
2. **O objetivo da sub-fase e o painel e a logica de negocio**: mostrar
   agregacao por nivel de severidade, contagem por host, e ranking de
   tecnicas MITRE ATT&CK - nao operar o agente Wazuh de fato em cada host.
3. **Mesma filosofia do ADR-003 (Backup)**: simular a fonte de dados,
   manter real a modelagem e a logica de consulta.

Optamos por:
- Modelar `SecurityEvent` como entidade de primeira classe no banco,
  com campos que espelham a saida real do Wazuh (rule_id, level, host,
  descricao) mais os campos de mapeamento MITRE ATT&CK (tactic,
  technique_id, technique_name).
- Popular via seed (`app/seed_security.py`) com 180 eventos ficticios
  distribuidos em 30 dias, usando um conjunto curado de 12 regras
  realistas (forca bruta SSH, escalonamento de privilegio, criacao de
  conta, alteracao de firewall, etc.), cada uma corretamente mapeada
  para uma tatica e tecnica real do MITRE ATT&CK.
- Calcular KPIs (contagem por nivel de severidade, hosts afetados,
  ranking de tecnicas) via agregacao SQL real sobre os dados simulados -
  a logica de consulta e de negocio e genuina, so a origem dos dados
  e fabricada.

## Consequencias

- O painel reflete uma arquitetura de dados e consultas agregadas
  prontas para uso real, mas os eventos individuais sao fabricados,
  nao coletados de agentes reais.
- Isso deve ficar claro em qualquer demonstracao do projeto, para nao
  passar a impressao de que ha deteccao de seguranca real acontecendo.
- Ao migrar para o servidor dedicado (Fase 9a) com mais RAM disponivel,
  avaliar a instalacao de um Wazuh real (ou alternativa mais leve como
  Suricata + ElastAlert) para substituir o seed por eventos de producao
  de fato, mantendo os mesmos endpoints e o mesmo formato de dados
  (`SecurityEvent`) para minimizar mudancas no frontend.
