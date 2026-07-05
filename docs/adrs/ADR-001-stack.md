# ADR-001 — Escolha da stack tecnologica

**Status:** Aceito
**Data:** 2026-07-05

## Contexto

O InfraNOC precisa demonstrar competencias de nivel Pleno/Senior para vagas de NOC/Infraestrutura, SysAdmin/AD e DevOps, rodando bem em laboratorio de 16GB RAM.

## Decisao

Backend em **Python 3.12 + FastAPI** (Clean Architecture: domain/application/infrastructure/api), SQLAlchemy 2.0 async, PostgreSQL, Redis, Alembic. Frontend em Next.js 15 + TypeScript. Observabilidade com Prometheus/Loki/Grafana. 2 VMs reais (Windows Server 2022 + Ubuntu 24.04) e ~330 ativos simulados via containers Python.

## Alternativas consideradas

- **.NET/C#:** descartado — Python casa melhor com o perfil de infra/DevOps e com automacao, simuladores e IA.
- **Microsservicos:** descartado — monolito modular (Clean Arch) entrega mais valor em lab solo.

## Consequencias

Stack unica em Python para backend/automacao/IA. Necessidade de simuladores para atingir escala de inventario sem RAM.
