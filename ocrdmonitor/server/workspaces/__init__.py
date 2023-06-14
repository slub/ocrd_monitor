from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from ocrdmonitor.server.settings import OcrdBrowserSettings

from ._launchroutes import register_launchroutes
from ._listroutes import register_listroutes
from ._proxyroutes import register_proxyroutes


def create_workspaces(
    templates: Jinja2Templates, browser_settings: OcrdBrowserSettings
) -> APIRouter:
    router = APIRouter(prefix="/workspaces")

    WORKSPACE_DIR = browser_settings.workspace_dir

    def full_workspace(workspace: Path | str) -> str:
        return str(WORKSPACE_DIR / workspace)

    register_listroutes(router, templates, browser_settings)
    register_launchroutes(router, templates, browser_settings, full_workspace)
    register_proxyroutes(router, templates, browser_settings, full_workspace)

    return router
