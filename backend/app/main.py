from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.application.ad_audit_job import collect_ad_events
from app.core.config import settings

app = FastAPI(title="InfraNOC API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

_scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def _start_scheduler() -> None:
    _scheduler.add_job(
        collect_ad_events,
        trigger="interval",
        minutes=settings.ad_audit_interval_minutes,
        id="ad_audit_job",
        replace_existing=True,
        misfire_grace_time=60,
    )
    _scheduler.start()


@app.on_event("shutdown")
async def _stop_scheduler() -> None:
    _scheduler.shutdown(wait=False)


@app.get("/health")
async def health():
    return {"status": "ok"}