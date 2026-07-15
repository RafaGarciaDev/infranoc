# InfraNOC

> Plataforma unificada de NOC, SOC, IAM e Observabilidade — monitorando a fábrica fictícia **Laticínios Vale Verde S/A**.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![CI](https://github.com/RafaGarciaDev/infranoc/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-009688)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![License](https://img.shields.io/badge/license-MIT-blue)

<!-- GIF HERO: substituir pelo GIF de 15s do dashboard NOC em ação -->
<!-- ![Demo do InfraNOC](docs/screenshots/hero.gif) -->

## Sobre

Plataforma enterprise que unifica observabilidade de TI e OT industrial, gestão de Active Directory, CMDB, alertas com impacto de negócio e um assistente de IA local (RAG + tool calling) — tudo monitorando uma indústria de laticínios fictícia com **333 ativos** e **250 usuários** em Active Directory real.

## Cenário

**Laticínios Vale Verde S/A** — indústria de médio porte, ~280 funcionários, operação 24/7 em 3 turnos. Matriz em Pouso Alegre/MG, filial comercial em São Paulo/SP. Produz leite UHT, queijos, iogurte e manteiga.

## Demo ao vivo

<!-- TODO: preencher após deploy (Fase 8, item 5) -->
🔗 **Acesse:** `<DOMINIO>`
👤 **Credenciais de demonstração:** `demo@valeverde.com` / `demo`
🎥 **Vídeo walkthrough (2min):** `<LINK_VIDEO>`

## Screenshots

<!-- TODO: substituir pelos screenshots reais (docs/screenshots/) -->
| Dashboard NOC | Assistente de IA (RAG local) | Mapa da planta |
|---|---|---|
| `<screenshot>` | `<screenshot>` | `<screenshot>` |

## Stack

**Backend:** Python 3.12 · FastAPI · SQLAlchemy · Alembic · PostgreSQL · pgvector · Redis
**IA:** Ollama (qwen2.5, local) · embeddings multilingue (e5-small) · tool calling + RAG híbrido
**Frontend:** Next.js 15 · TypeScript · Tailwind · shadcn/ui · ECharts
**Observabilidade:** Prometheus · Loki · Grafana · AlertManager
**Infra:** Docker · Active Directory · ldap3 · WebSocket
**Integrações:** Peppermint (ITSM) · Vikunja (gestão de tarefas)

## Módulos (MVP)

Dashboard NOC · Observabilidade TI · Observabilidade OT (OEE/HACCP) · Rede · Energia/Infra física · Active Directory · Impressoras · CMDB · Alertas · Automação de chamados · **Assistente de IA local (RAG + tool calling)**

## Arquitetura

<!-- TODO: renderizar docs/diagrams/c4-container.mmd aqui, ou embutir com mermaid -->
Diagramas C4 (contexto, container), ER e sequência (fluxo de alerta) em [`docs/diagrams/`](docs/diagrams/).

## Subir tudo com 1 comando

```powershell
# 1. Copiar .env.example -> .env (fica gitignored)
Copy-Item .env.example .env

# 2. Subir a stack de observabilidade primeiro (cria a network)
docker compose -f compose\docker-compose.observability.yml up -d

# 3. Subir dev (postgres + redis + backend + web)
docker compose -f compose\docker-compose.dev.yml up -d --build

# 4. Rodar seed (uma vez)
docker exec infranoc-backend uv run python -m app.seed
```

Endpoints:
- Frontend: http://localhost:3000
- Backend: http://localhost:8080 (docs em `/docs`)
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

## Testes

```powershell
uv run pytest
```

Cobertura inclui teste de **isolamento multi-tenant** (garante que dados de um tenant nunca vazam para outro).

## Decisões de arquitetura

Ver [`docs/adrs/`](docs/adrs/) — incluindo o [ADR-002](docs/adrs/ADR-002-ia-hibrido-tool-calling-rag.md), que documenta o design híbrido de tool calling + RAG para o assistente de IA local.

## Roadmap

**Feito (✅):**
Dashboard NOC · Observabilidade TI/OT · CMDB · Alertas com contexto de negócio · Active Directory real · Assistente de IA local (RAG + tool calling) · ITSM (Peppermint) · Gestão de tarefas (Vikunja)

**Evolução futura:**
- Backup (Veeam)
- Segurança / SIEM (Wazuh + MITRE ATT&CK)
- Automação de rede (Mikrotik/Ubiquiti)
- Help Desk avançado
- VPN + sessões de usuários logados

## Status

Em desenvolvimento. Projeto de portfólio demonstrando competências de nível Pleno/Sênior.

## Autor

**RafaGarciaDev** — [LinkedIn](https://www.linkedin.com/in/rafael-farias-garcia-6617b246/) · [GitHub](https://github.com/RafaGarciaDev)

## Licença

MIT
