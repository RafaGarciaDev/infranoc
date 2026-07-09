#!/bin/sh
set -e
echo "[entrypoint] applying alembic migrations..."
uv run alembic upgrade head
echo "[entrypoint] starting uvicorn with reload..."
exec uv run uvicorn app.main:app \
    --host 0.0.0.0 --port 8080 \
    --reload --reload-dir /app/app