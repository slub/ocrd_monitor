from __future__ import annotations

import asyncio
import logging
import os
from shutil import which
from typing import Optional

from ._browser import OcrdBrowser, OcrdBrowserClient
from ._port import Port
from ._client import HttpBrowserClient

BROADWAY_BASE_PORT = 8080


class SubProcessOcrdBrowser:
    def __init__(self, localport: Port, owner: str, workspace: str) -> None:
        self._localport = localport
        self._owner = owner
        self._workspace = workspace
        self._process: Optional[asyncio.subprocess.Process] = None

    def address(self) -> str:
        # as long as we do not have a reverse proxy on BW_PORT,
        # we must map the local port range to the exposed range
        # (we use 8085 as fixed start of the internal port range,
        #  and map to the runtime corresponding external port)
        localport = self._localport.get()
        return "http://localhost:" + str(localport)

    def workspace(self) -> str:
        return self._workspace

    def owner(self) -> str:
        return self._owner

    async def start(self) -> None:
        browse_ocrd = which("browse-ocrd")
        if not browse_ocrd:
            raise FileNotFoundError("Could not find browse-ocrd executable")
        localport = self._localport.get()
        # broadwayd (which uses WebSockets) only allows a single client at a time
        # (disconnecting concurrent connections), hence we must start a new daemon
        # for each new browser session
        # broadwayd starts counting virtual X displays from port 8080 as :0
        displayport = str(localport - BROADWAY_BASE_PORT)
        environment = dict(os.environ)
        environment["GDK_BACKEND"] = "broadway"
        environment["BROADWAY_DISPLAY"] = ":" + displayport

        self._process = await asyncio.create_subprocess_shell(
            " ".join(
                [
                    "broadwayd",
                    ":" + displayport + " &",
                    browse_ocrd,
                    self._workspace + "/mets.xml ;",
                    "kill $!",
                ]
            ),
            env=environment,
        )

    async def stop(self) -> None:
        if self._process:
            try:
                self._process.terminate()
            except ProcessLookupError:
                logging.info(
                    f"Attempted to stop already terminated process {self._process.pid}"
                )
            finally:
                self._localport.release()

    def client(self) -> OcrdBrowserClient:
        return HttpBrowserClient(self.address())


class SubProcessOcrdBrowserFactory:
    def __init__(self, available_ports: set[int]) -> None:
        self._available_ports = available_ports

    def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        return SubProcessOcrdBrowser(Port(self._available_ports), owner, workspace_path)
