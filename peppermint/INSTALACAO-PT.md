# Peppermint — Instalação (Docker nativo)

Versão customizada: **tema escuro por padrão** e **interface em português**.

## Requisitos
- Docker 24+ e Docker Compose v2 (`docker compose version`)

## Passo a passo

```bash
# 1. Configure as variáveis de ambiente
cp .env.example .env
nano .env   # troque DB_PASSWORD e SECRET

# 2. Compile e suba os containers (build nativo, a partir do código local)
docker compose up -d --build

# 3. Acompanhe os logs até a aplicação subir
docker compose logs -f peppermint
```

## Acesso
- Interface web: http://localhost:3000
- API: http://localhost:5003

**Login padrão inicial:**
- E-mail: `admin@admin.com`
- Senha: `1234`

> Troque a senha do admin logo após o primeiro login.

## O que foi customizado
1. **Tema escuro como padrão** — `pages/_app.tsx`, `components/ThemeSettings/index.tsx` e script anti-flash em `pages/_document.js`. O usuário ainda pode trocar o tema nas configurações.
2. **Português como idioma padrão** — `apps/client/i18n.js` (`defaultLocale: "pt"`, detecção automática desativada), tradução PT completada (`locales/pt/peppermint.json`) e telas de login/cadastro/recuperação de senha traduzidas.
3. **Docker nativo** — `docker-compose.yml` agora compila a imagem a partir do código local (`build: .`) em vez de baixar `pepperlabs/peppermint` do Docker Hub, com:
   - Postgres 16 (alpine) com **healthcheck** — a aplicação só sobe depois do banco estar pronto
   - Variáveis via arquivo `.env`
   - Rede dedicada, `restart: unless-stopped` e fuso horário `America/Sao_Paulo`

## Comandos úteis
```bash
docker compose down             # parar
docker compose up -d --build    # rebuild após alterar o código
docker compose logs -f          # logs
docker volume rm peppermint-main_pgdata   # zerar o banco (apaga tudo!)
```
