from __future__ import annotations

import asyncio


from ocrdbrowser import HttpBrowserClient, OcrdBrowserClient

from ._backgroundprocess import BackgroundProcess
from ._broadwayfake import broadway_fake


class BrowserFake:
    def __init__(self, owner: str = "", workspace: str = "") -> None:
        self._owner: str = owner
        self._workspace: str = workspace
        self._browser = broadway_fake(workspace)
        self._running = False

    def set_owner_and_workspace(self, owner: str, workspace: str) -> None:
        self._owner = owner
        self._workspace = workspace
        self._browser = broadway_fake(workspace)

    def process_id(self) -> str:
        return str(self._browser.pid)

    def address(self) -> str:
        return "http://localhost:7000"

    def owner(self) -> str:
        return self._owner

    def workspace(self) -> str:
        return self._workspace

    def client(self) -> OcrdBrowserClient:
        return HttpBrowserClient(self.address())

    async def start(self) -> None:
        self._running = True
        await asyncio.to_thread(self._browser.launch)

    async def stop(self) -> None:
        self._running = False
        await asyncio.to_thread(self._browser.shutdown)

    @property
    def broadway_server(self) -> BackgroundProcess:
        return self._browser

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_server_running(self) -> bool:
        return self._browser.is_running
