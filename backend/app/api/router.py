from fastapi import APIRouter

from app.api.routes import auth

# Conforme as fases avançam, mais routers entram aqui:
#   assets (Fase 4), directory (Fase 5), dashboard (Fase 6),
#   alerts (Fase 3), ai (Fase 7)

api_router = APIRouter()
api_router.include_router(auth.router)
