from fastapi import APIRouter
from app.api.routes import ai, alerts, assets, assets_import, auth, dashboard, directory, hub, integrations, linux_ops, sectors, tickets, wiki
# Conforme as fases avancam, mais routers entram aqui:
#   assets (Fase 4), directory (Fase 5), dashboard (Fase 6),
#   alerts (Fase 3 - Bloco 4), ai (Fase 7)
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(alerts.router)
api_router.include_router(assets.router)
api_router.include_router(assets_import.router)
api_router.include_router(sectors.router)
api_router.include_router(directory.router)
api_router.include_router(dashboard.router)
api_router.include_router(integrations.router)
api_router.include_router(tickets.router)
api_router.include_router(ai.router)
api_router.include_router(wiki.router)
api_router.include_router(hub.router)
api_router.include_router(linux_ops.router_linux)
api_router.include_router(linux_ops.router_toolkit)

