from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.templating import Jinja2Templates

from ocrdbrowser import OcrdBrowserFactory
from ocrdmonitor.protocols import BrowserProcessRepository, Environment

from ._launchroutes import register_launchroutes
from ._listroutes import register_listroutes
from ._proxyroutes import register_proxyroutes


def create_workspaces(
    templates: Jinja2Templates, environment: Environment
) -> APIRouter:
    router = APIRouter(prefix="/workspaces")

    browser_settings = environment.settings.ocrd_browser
    WORKSPACE_DIR = browser_settings.workspace_dir

    def full_workspace(workspace: Path | str) -> str:
        return str(WORKSPACE_DIR / workspace)

    async def get_browser_repository() -> BrowserProcessRepository:
        return (await environment.repositories()).browser_processes

    browser_repository = Depends(get_browser_repository)
    browser_factory = Depends(environment.browser_factory)

    register_listroutes(router, templates, browser_settings)
    register_launchroutes(
        router, templates, browser_factory, browser_repository, full_workspace
    )
    register_proxyroutes(router, templates, browser_repository, full_workspace)

    return router
