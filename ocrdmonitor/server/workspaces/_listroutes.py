from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from ocrdbrowser import workspace
from ocrdmonitor.server.settings import OcrdBrowserSettings


def register_listroutes(
    router: APIRouter, templates: Jinja2Templates, browser_settings: OcrdBrowserSettings
) -> None:
    @router.get("/", name="workspaces.list")
    def list_workspaces(request: Request) -> Response:
        spaces = [
            Path(space).relative_to(browser_settings.workspace_dir)
            for space in workspace.list_all(browser_settings.workspace_dir)
        ]

        return templates.TemplateResponse(
            "list_workspaces.html.j2",
            {"request": request, "workspaces": spaces},
        )
