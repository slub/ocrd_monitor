from __future__ import annotations

import asyncio
import functools
import logging
import os
import signal
from shutil import which
from typing import NamedTuple, Type, cast

from ._browser import OcrdBrowser, OcrdBrowserClient
from ._client import HttpBrowserClient
from ._port import PortBindingError, PortBindingResult, try_bind

BROADWAY_BASE_PORT = 8080


class BroadwayBrowserId(NamedTuple):
    broadway_pid: int
    browser_pid: int

    @classmethod
    def from_str(cls: Type["BroadwayBrowserId"], id_str: str) -> "BroadwayBrowserId":
        ids = map(int, id_str.split("-"))
        return BroadwayBrowserId(*ids)

    def __str__(self) -> str:
        return f"{self.broadway_pid}-{self.browser_pid}"


class SubProcessOcrdBrowser:
    def __init__(
        self, owner: str, workspace: str, address: str, process_id: str
    ) -> None:
        self._owner = owner
        self._workspace = workspace
        self._address = address
        self._process_id = BroadwayBrowserId.from_str(process_id)

    def process_id(self) -> str:
        return str(self._process_id)

    def address(self) -> str:
        return self._address

    def workspace(self) -> str:
        return self._workspace

    def owner(self) -> str:
        return self._owner

    async def stop(self) -> None:
        self._try_kill(self._process_id.broadway_pid)
        self._try_kill(self._process_id.browser_pid)

    @staticmethod
    def _try_kill(pid: int) -> None:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            logging.warning(f"Could not find process with ID {pid}")

    def client(self) -> OcrdBrowserClient:
        return HttpBrowserClient(self.address())


class ProcessLaunchFailedError(RuntimeError):
    pass


class SubProcessOcrdBrowserFactory:
    def __init__(self, available_ports: set[int]) -> None:
        self._available_ports = available_ports

    async def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        port_binding = functools.partial(start_browser, workspace_path)
        pid, port = await try_bind(
            port_binding, "http://localhost", self._available_ports
        )

        address = f"http://localhost:{port}"
        return SubProcessOcrdBrowser(owner, workspace_path, address, str(pid))


async def start_browser(
    workspace: str, host: str, port: int
) -> PortBindingResult[BroadwayBrowserId]:
    find_executables_or_raise()

    # broadwayd (which uses WebSockets) only allows a single client at a time
    # (disconnecting concurrent connections), hence we must start a new daemon
    # for each new browser session
    # broadwayd starts counting virtual X displays from port 8080 as :0
    displayport = str(port - BROADWAY_BASE_PORT)

    try:
        broadway_process = await launch_broadway(displayport)

        if broadway_process is None:
            return PortBindingError()

        environment = prepare_env(displayport)
        full_cmd = browser_command(workspace, broadway_process.pid)
        browser_process = await asyncio.create_subprocess_shell(
            full_cmd, env=environment
        )

        return BroadwayBrowserId(broadway_process.pid, browser_process.pid)
    except Exception as err:
        logging.error(f"Failed to launch broadway at (real port {port})")
        logging.error(repr(err))
        return PortBindingError()


def find_executables_or_raise() -> None:
    if not which("broadwayd"):
        raise FileNotFoundError("Could not find broadwayd executable")

    if not which("browse-ocrd"):
        raise FileNotFoundError("Could not find browse-ocrd executable")


async def launch_broadway(
    displayport: str,
) -> asyncio.subprocess.Process | None:
    broadway = cast(str, which("broadwayd"))
    broadway_process = await asyncio.create_subprocess_exec(
        broadway, f":{displayport}", stderr=asyncio.subprocess.PIPE
    )

    try:
        stderr = cast(asyncio.StreamReader, broadway_process.stderr)
        err_output = await asyncio.wait_for(stderr.readline(), 5)
        if b"Address already in use" in err_output:
            return None
    except asyncio.TimeoutError:
        logging.info(
            "The process didn't exit within the given timeout."
            + f"Assuming broadway on port {displayport} launched successfully"
        )

    return broadway_process


def prepare_env(displayport: str) -> dict[str, str]:
    environment = dict(os.environ)
    environment["GDK_BACKEND"] = "broadway"
    environment["BROADWAY_DISPLAY"] = ":" + displayport
    return environment


def browser_command(workspace: str, broadway_pid: int) -> str:
    mets_path = workspace + "/mets.xml"
    kill_broadway = f"; kill {broadway_pid}"
    browse_ocrd = cast(str, which("browse-ocrd"))
    return " ".join(
        [
            browse_ocrd,
            "-mr",
            mets_path,
            kill_broadway,
        ]
    )
