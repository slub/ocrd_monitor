from __future__ import annotations

from fastapi import APIRouter

from ocrdmonitor.protocols import Environment

from .routers import workspaces
from .routers import jobs

def create_api(
     environment: Environment
) -> APIRouter:
    router = APIRouter(prefix="/api")

    router.include_router(workspaces.router(browser_settings=environment.settings.ocrd_browser))
    router.include_router(jobs.router(environment))
    return router
