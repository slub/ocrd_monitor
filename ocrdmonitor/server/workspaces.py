from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import ocrdbrowser
import ocrdmonitor.server.proxy as proxy
from fastapi import APIRouter, Cookie, Request, Response, WebSocket
from fastapi.templating import Jinja2Templates
from ocrdbrowser import ChannelClosed, OcrdBrowser, OcrdBrowserFactory, workspace
from ocrdmonitor.server.redirect import RedirectMap
from requests.exceptions import ConnectionError


def create_workspaces(
    templates: Jinja2Templates, factory: OcrdBrowserFactory, workspace_dir: Path
) -> APIRouter:
    router = APIRouter(prefix="/workspaces")

    running_browsers: set[OcrdBrowser] = set()
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
    async def browser(request: Request, workspace: str) -> Response:
        workspace_path = workspace_dir / workspace
        session_id = request.cookies.setdefault("session_id", str(uuid.uuid4()))
        response = Response()
        response.set_cookie("session_id", session_id)

        browser = await launch_browser(session_id, workspace_path)
        redirects.add(session_id, Path(workspace), browser)

        return response

    @router.get("/open/{workspace:path}", name="workspaces.open")
    def open_workspace(request: Request, workspace: str) -> Response:
        return templates.TemplateResponse(
            "workspace.html.j2",
            {"request": request, "workspace": workspace},
        )

    @router.get("/ping/{workspace:path}", name="workspaces.ping")
    def ping_workspace(
        request: Request, workspace: str, session_id: str = Cookie(default=None)
    ) -> Response:
        workspace_path = Path(workspace)
        redirect = redirects.get(session_id, workspace_path)
        try:
            proxy.forward(redirect, str(workspace_path))
            return Response(status_code=200)
        except ConnectionError:
            return Response(status_code=502)

    # NOTE: It is important that the route path here ends with a slash, otherwise
    #       the reverse routing will not work as broadway.js uses window.location
    #       which points to the last component with a trailing slash.
    @router.get("/view/{workspace:path}/", name="workspaces.view")
    def workspace_reverse_proxy(
        request: Request, workspace: str, session_id: str = Cookie(default=None)
    ) -> Response:
        workspace_path = Path(workspace)
        redirect = redirects.get(session_id, workspace_path)
        try:
            return proxy.forward(redirect, str(workspace_path))
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
        async with browser.open_channel() as channel:
            try:
                while True:
                    await proxy.tunnel(channel, websocket)
            except ChannelClosed:
                browser.stop()

    async def launch_browser(session_id: str, workspace: Path) -> OcrdBrowser:
        browser = await asyncio.to_thread(
            ocrdbrowser.launch,
            str(workspace),
            session_id,
            factory,
            running_browsers,
        )

        running_browsers.add(browser)
        return browser

    return router
