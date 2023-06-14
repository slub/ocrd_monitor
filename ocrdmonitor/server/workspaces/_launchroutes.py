from typing import Callable
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.templating import Jinja2Templates

from ocrdbrowser import OcrdBrowserFactory
from ocrdmonitor.browserprocess import BrowserProcessRepository
from ocrdmonitor.server.settings import OcrdBrowserSettings


def session_response(session_id: str) -> Response:
    response = Response()
    response.set_cookie("session_id", session_id)
    return response


def register_launchroutes(
    router: APIRouter,
    templates: Jinja2Templates,
    browser_settings: OcrdBrowserSettings,
    full_workspace: Callable[[str | Path], str],
) -> None:
    @router.get("/open/{workspace:path}", name="workspaces.open")
    def open_workspace(request: Request, workspace: str) -> Response:
        return templates.TemplateResponse(
            "workspace.html.j2",
            {"request": request, "workspace": workspace},
        )

    @router.get("/browse/{workspace:path}", name="workspaces.browse")
    async def browser(
        request: Request,
        workspace: Path,
        factory: OcrdBrowserFactory = Depends(browser_settings.factory),
        repository: BrowserProcessRepository = Depends(browser_settings.repository),
    ) -> Response:
        session_id = request.cookies.setdefault("session_id", str(uuid.uuid4()))

        full_path = full_workspace(workspace)
        existing_browsers = await repository.find(owner=session_id, workspace=full_path)

        if not existing_browsers:
            browser = await factory(session_id, full_path)
            await repository.insert(browser)

        return session_response(session_id)
