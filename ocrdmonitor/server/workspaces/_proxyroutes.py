from __future__ import annotations

import functools
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Cookie, Depends, Request, Response, WebSocket
from fastapi.templating import Jinja2Templates

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.browserprocess import BrowserProcessRepository
from ocrdmonitor.server.settings import OcrdBrowserSettings

from ._browsercommunication import CloseCallback, communicate_until_closed, forward


async def stop_and_remove_browser(
    repository: BrowserProcessRepository, browser: OcrdBrowser
) -> None:
    await browser.stop()
    await repository.delete(browser)


async def first_owned_browser_in_workspace(
    session_id: str, workspace: str, repository: BrowserProcessRepository
) -> OcrdBrowser | None:
    def in_workspace(browser: OcrdBrowser) -> bool:
        return workspace.startswith(browser.workspace())

    browsers_in_workspace = filter(
        in_workspace, await repository.find(owner=session_id)
    )
    return next(browsers_in_workspace, None)


def browser_closed_callback(reposository: BrowserProcessRepository) -> CloseCallback:
    return functools.partial(stop_and_remove_browser, reposository)


def register_proxyroutes(
    router: APIRouter,
    templates: Jinja2Templates,
    browser_settings: OcrdBrowserSettings,
    full_workspace: Callable[[str | Path], str],
) -> None:
    @router.get("/ping/{workspace:path}", name="workspaces.ping")
    async def ping_workspace(
        workspace: Path,
        session_id: str = Cookie(),
        repository: BrowserProcessRepository = Depends(browser_settings.repository),
    ) -> Response:
        browser = await repository.first(
            owner=session_id, workspace=full_workspace(workspace)
        )

        if not browser:
            return Response(status_code=404)

        try:
            await forward(browser, str(workspace))
            return Response(status_code=200)
        except ConnectionError:
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
        browser = await first_owned_browser_in_workspace(
            session_id, full_workspace(workspace), repository
        )

        if not browser:
            return Response(
                content=f"No browser found for {workspace}", status_code=404
            )
        try:
            return await forward(browser, str(workspace))
        except ConnectionError:
            await stop_and_remove_browser(repository, browser)
            return templates.TemplateResponse(
                "view_workspace_failed.html.j2",
                {"request": request, "workspace": workspace},
            )

    @router.websocket("/view/{workspace:path}/socket", name="workspaces.view.socket")
    async def workspace_socket_proxy(
        websocket: WebSocket,
        workspace: Path,
        session_id: str = Cookie(),
        repository: BrowserProcessRepository = Depends(browser_settings.repository),
    ) -> None:
        browser = await repository.first(
            owner=session_id, workspace=full_workspace(workspace)
        )

        if browser is None:
            await websocket.close(reason="No browser found")
            return

        await websocket.accept(subprotocol="broadway")
        await communicate_until_closed(
            websocket,
            browser,
            close_callback=browser_closed_callback(repository),
        )
