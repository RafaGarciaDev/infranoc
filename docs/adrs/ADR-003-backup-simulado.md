# ADR-003: Painel de Backup com dados simulados (sem Veeam real no lab)

## Status
Aceito

## Contexto

A Fase 9f pede um painel de backup mostrando jobs, sucesso/falha, retention,
restore points e alertas de RPO/RTO. A ferramenta de referencia do mercado
para esse tipo de gestao e o Veeam Backup & Replication.

## Decisao

Nao rodamos uma instancia real do Veeam no laboratorio. Os motivos:

1. **Custo de infraestrutura desproporcional**: Veeam B&R exige Windows
   Server + SQL Server (ou SQL Express) + licenca, para um laboratorio que
   ja roda 14+ containers em hardware limitado (16GB de RAM).
2. **O objetivo da sub-fase e o painel, nao o produto de backup em si**:
   o valor de portfolio esta na modelagem de dados (jobs, restore points,
   RPO/RTO), na UI, e na integracao com o sistema de alertas (Fase 3) -
   nao em operar o Veeam de fato.
3. **Arquitetura plugavel**: o design permite que uma instancia real do
   Veeam seja conectada no futuro sem reescrever o painel.

Optamos por:
- Modelar `BackupJob` e `RestorePoint` como entidades de primeira classe
  no banco (nao mockadas em memoria).
- Popular via seed (`app/seed_backup.py`) com 10 jobs ficticios e
  historico real de restore points (gerados com timestamps, tamanhos e
  status realistas, incluindo falhas ocasionais).
- Calcular RPO real (tempo desde o ultimo restore point bem-sucedido)
  dinamicamente a cada consulta, comparando com a meta (`rpo_target_hours`)
  - ou seja, a logica de negocio e real, so os dados de origem sao
  simulados.
- Deixar a porta aberta para um `VeeamClient` real: quando/se o Veeam for
  instalado (real ou em outro ambiente), basta implementar um cliente que
  chame a API REST do Veeam Enterprise Manager e substitua a fonte de
  dados do seed por chamadas reais, sem alterar os endpoints ja
  consumidos pelo frontend.

## Consequencias

- O painel de backup no InfraNOC reflete uma arquitetura de dados e uma
  UI prontas para producao, mas os "resultados de backup" que ele mostra
  sao fabricados, nao operacoes reais executadas no lab.
- Isso deve ficar claro em qualquer demonstracao do projeto (README,
  video, entrevista) para nao passar a impressao de que ha um Veeam de
  verdade rodando.
- Se o projeto crescer para o servidor dedicado (Fase 9a) com mais RAM
  disponivel, avaliar a instalacao de um Veeam real (ou alternativa
  open-source como o Bacula/Duplicati) para substituir o seed por dados
  de producao de fato.
