from __future__ import annotations

import asyncio
import os
import signal
from shutil import which

from ._browser import OcrdBrowser, OcrdBrowserClient
from ._client import HttpBrowserClient
from ._port import Port

BROADWAY_BASE_PORT = 8080


class SubProcessOcrdBrowser:
    def __init__(
        self, owner: str, workspace: str, address: str, process_id: str
    ) -> None:
        self._owner = owner
        self._workspace = workspace
        self._address = address
        self._process_id = process_id

    def process_id(self) -> str:
        return self._process_id

    def address(self) -> str:
        return self._address

    def workspace(self) -> str:
        return self._workspace

    def owner(self) -> str:
        return self._owner

    async def stop(self) -> None:
        os.kill(int(self._process_id), signal.SIGKILL)

    def client(self) -> OcrdBrowserClient:
        return HttpBrowserClient(self.address())


class SubProcessOcrdBrowserFactory:
    def __init__(self, available_ports: set[int]) -> None:
        self._available_ports = available_ports

    async def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        port = Port(self._available_ports).get()
        address = f"https://localhost:{port}"
        process = await self.start_browser(workspace_path, port)
        browser = SubProcessOcrdBrowser(
            owner, workspace_path, address, str(process.pid)
        )
        return browser

    async def start_browser(
        self, workspace: str, port: int
    ) -> asyncio.subprocess.Process:
        browse_ocrd = which("browse-ocrd")
        if not browse_ocrd:
            raise FileNotFoundError("Could not find browse-ocrd executable")

        # broadwayd (which uses WebSockets) only allows a single client at a time
        # (disconnecting concurrent connections), hence we must start a new daemon
        # for each new browser session
        # broadwayd starts counting virtual X displays from port 8080 as :0
        displayport = str(port - BROADWAY_BASE_PORT)
        environment = dict(os.environ)
        environment["GDK_BACKEND"] = "broadway"
        environment["BROADWAY_DISPLAY"] = ":" + displayport

        return await asyncio.create_subprocess_shell(
            " ".join(
                [
                    "broadwayd",
                    ":" + displayport + " &",
                    browse_ocrd,
                    workspace + "/mets.xml ;",
                    "kill $!",
                ]
            ),
            env=environment,
        )
