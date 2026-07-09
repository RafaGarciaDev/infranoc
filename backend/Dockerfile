FROM python:3.12-slim

# Instala uv
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias primeiro (cache-friendly)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Codigo depois
COPY . .

# Instala o proprio projeto (nao remonta a venv se so o codigo mudou)
RUN uv sync --frozen

EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]