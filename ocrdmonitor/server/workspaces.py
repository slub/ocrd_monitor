from __future__ import annotations

import uuid
from pathlib import Path


import ocrdbrowser
from ocrdmonitor import dbmodel
import ocrdmonitor.server.proxy as proxy
from fastapi import APIRouter, Cookie, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from ocrdbrowser import ChannelClosed, OcrdBrowser, OcrdBrowserFactory, workspace
from ocrdmonitor.server.redirect import RedirectMap


def create_workspaces(
    templates: Jinja2Templates, factory: OcrdBrowserFactory, workspace_dir: Path
) -> APIRouter:
    router = APIRouter(prefix="/workspaces")

    redirects = RedirectMap()

    @router.get("/", name="workspaces.list")
    def list_workspaces(request: Request) -> Response:
        spaces = [
            Path(space).relative_to(workspace_dir)
            for space in workspace.list_all(workspace_dir)
        ]

        return templates.TemplateResponse(
            "list_workspaces.html.j2",
            {"request": request, "workspaces": spaces},
        )

    @router.get("/browse/{workspace:path}", name="workspaces.browse")
    async def browser(request: Request, workspace: Path) -> Response:
        session_id = request.cookies.setdefault("session_id", str(uuid.uuid4()))
        response = Response()
        response.set_cookie("session_id", session_id)

        if (session_id, workspace) not in redirects:
            browser = await launch_browser(session_id, workspace)
            redirects.add(session_id, workspace, browser)
            await dbmodel.BrowserProcess(  # type: ignore
                process_id=browser.process_id(),
                owner=browser.owner(),
                workspace=browser.workspace(),
            ).insert()

        return response

    @router.get("/open/{workspace:path}", name="workspaces.open")
    def open_workspace(request: Request, workspace: str) -> Response:
        return templates.TemplateResponse(
            "workspace.html.j2",
            {"request": request, "workspace": workspace},
        )

    @router.get("/ping/{workspace:path}", name="workspaces.ping")
    async def ping_workspace(
        request: Request, workspace: Path, session_id: str = Cookie(default=None)
    ) -> Response:
        redirect = redirects.get(session_id, workspace)
        try:
            await proxy.forward(redirect, str(workspace))
            return Response(status_code=200)
        except ConnectionError:
            return Response(status_code=502)

    # NOTE: It is important that the route path here ends with a slash, otherwise
    #       the reverse routing will not work as broadway.js uses window.location
    #       which points to the last component with a trailing slash.
    @router.get("/view/{workspace:path}/", name="workspaces.view")
    async def workspace_reverse_proxy(
        request: Request, workspace: Path, session_id: str = Cookie(default=None)
    ) -> Response:
        redirect = redirects.get(session_id, workspace)
        try:
            return await proxy.forward(redirect, str(workspace))
        except ConnectionError:
            return templates.TemplateResponse(
                "view_workspace_failed.html.j2",
                {"request": request, "workspace": workspace},
            )

    @router.websocket("/view/{workspace:path}/socket", name="workspaces.view.socket")
    async def workspace_socket_proxy(
        websocket: WebSocket, workspace: Path, session_id: str = Cookie(default=None)
    ) -> None:
        redirect = redirects.get(session_id, workspace)
        await websocket.accept(subprotocol="broadway")
        await communicate_with_browser_until_closed(websocket, redirect.browser)

    async def communicate_with_browser_until_closed(
        websocket: WebSocket, browser: OcrdBrowser
    ) -> None:
        async with browser.client().open_channel() as channel:
            try:
                while True:
                    await proxy.tunnel(channel, websocket)
            except ChannelClosed:
                await stop_browser(browser)
            except WebSocketDisconnect:
                pass

    async def launch_browser(session_id: str, workspace: Path) -> OcrdBrowser:
        full_workspace_path = workspace_dir / workspace
        return await ocrdbrowser.launch(str(full_workspace_path), session_id, factory)

    async def stop_browser(browser: OcrdBrowser) -> None:
        await browser.stop()
        key = Path(browser.workspace()).relative_to(workspace_dir)
        redirects.remove(browser.owner(), key)

    return router
