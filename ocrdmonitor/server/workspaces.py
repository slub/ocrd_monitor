from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.templating import Jinja2Templates

from ocrdbrowser import ChannelClosed, OcrdBrowser, OcrdBrowserFactory, workspace
from ocrdmonitor.browserprocess import BrowserProcessRepository
from ocrdmonitor.server import proxy
from ocrdmonitor.server.settings import OcrdBrowserSettings


def create_workspaces(
    templates: Jinja2Templates,
    browser_settings: OcrdBrowserSettings,
) -> APIRouter:
    router = APIRouter(prefix="/workspaces")

    WORKSPACE_DIR = browser_settings.workspace_dir

    @router.get("/", name="workspaces.list")
    def list_workspaces(request: Request) -> Response:
        spaces = [
            Path(space).relative_to(WORKSPACE_DIR)
            for space in workspace.list_all(WORKSPACE_DIR)
        ]

        return templates.TemplateResponse(
            "list_workspaces.html.j2",
            {"request": request, "workspaces": spaces},
        )

    @router.get("/browse/{workspace:path}", name="workspaces.browse")
    async def browser(
        request: Request,
        workspace: Path,
        factory: OcrdBrowserFactory = Depends(browser_settings.factory),
        repository: BrowserProcessRepository = Depends(browser_settings.repository),
    ) -> Response:
        session_id = request.cookies.setdefault("session_id", str(uuid.uuid4()))
        response = Response()
        response.set_cookie("session_id", session_id)

        full_workspace = str(WORKSPACE_DIR / workspace)
        existing_browsers = await repository.find(
            owner=session_id, workspace=full_workspace
        )

        if not existing_browsers:
            browser = await launch_browser(factory, session_id, workspace)
            await repository.insert(browser)

        return response

    @router.get("/open/{workspace:path}", name="workspaces.open")
    def open_workspace(request: Request, workspace: str) -> Response:
        return templates.TemplateResponse(
            "workspace.html.j2",
            {"request": request, "workspace": workspace},
        )

    @router.get("/ping/{workspace:path}", name="workspaces.ping")
    async def ping_workspace(
        workspace: Path,
        session_id: str = Cookie(),
        repository: BrowserProcessRepository = Depends(browser_settings.repository),
    ) -> Response:
        browser = await repository.first(
            owner=session_id, workspace=str(WORKSPACE_DIR / workspace)
        )

        if not browser:
            return Response(status_code=404)

        try:
            await proxy.forward(browser, str(workspace))
            return Response(status_code=200)
        except (ConnectionError, IndexError):
            return Response(status_code=502)

    # NOTE: It is important that the route path here ends with a slash, otherwise
    #       the reverse routing will not work as broadway.js uses window.location
    #       which points to the last component with a trailing slash.
    @router.get("/view/{workspace:path}/", name="workspaces.view")
    async def workspace_reverse_proxy(
        request: Request,
        workspace: Path,
        session_id: str = Cookie(),
        repository: BrowserProcessRepository = Depends(browser_settings.repository),
    ) -> Response:
        requested_path = str(WORKSPACE_DIR / workspace)
        browsers = [
            b
            for b in await repository.find(owner=session_id)
            if requested_path.startswith(b.workspace())
        ]

        try:
            browser = browsers.pop()
            return await proxy.forward(browser, str(workspace))
        except ConnectionError:
            await stop_browser(repository, browser)
            return templates.TemplateResponse(
                "view_workspace_failed.html.j2",
                {"request": request, "workspace": workspace},
            )
        except IndexError:
            return Response(
                content=f"No browser found for {workspace}", status_code=404
            )

    @router.websocket("/view/{workspace:path}/socket", name="workspaces.view.socket")
    async def workspace_socket_proxy(
        websocket: WebSocket,
        workspace: Path,
        session_id: str = Cookie(),
        repository: BrowserProcessRepository = Depends(browser_settings.repository),
    ) -> None:
        browser = await repository.first(
            owner=session_id, workspace=str(WORKSPACE_DIR / workspace)
        )

        if browser is None:
            await websocket.close(reason="No browser found")
            return

        await websocket.accept(subprotocol="broadway")
        await communicate_with_browser_until_closed(repository, websocket, browser)

    async def communicate_with_browser_until_closed(
        repository: BrowserProcessRepository, websocket: WebSocket, browser: OcrdBrowser
    ) -> None:
        async with browser.client().open_channel() as channel:
            try:
                while True:
                    await proxy.tunnel(channel, websocket)
            except ChannelClosed:
                await stop_browser(repository, browser)
            except WebSocketDisconnect:
                pass

    async def launch_browser(
        factory: OcrdBrowserFactory, session_id: str, workspace: Path
    ) -> OcrdBrowser:
        full_workspace_path = WORKSPACE_DIR / workspace
        return await factory(session_id, str(full_workspace_path))

    async def stop_browser(
        repository: BrowserProcessRepository, browser: OcrdBrowser
    ) -> None:
        await browser.stop()
        await repository.delete(browser)

    return router
