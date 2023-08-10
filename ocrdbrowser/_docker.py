from __future__ import annotations

import asyncio
import functools
import logging
import os.path as path
from typing import Any

from ._browser import OcrdBrowser, OcrdBrowserClient
from ._client import HttpBrowserClient
from ._port import PortBindingError, PortBindingResult, try_bind

_docker_run = "docker run --rm -d --name {} -v {}:/data -p {}:8085 ocrd-browser:latest"
_docker_stop = "docker stop {}"
_docker_kill = "docker kill {}"


async def run_command(cmd: str, *args: Any) -> asyncio.subprocess.Process:
    command = cmd.format(*args)
    return await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


class DockerOcrdBrowser:
    def __init__(
        self, owner: str, workspace: str, address: str, process_id: str
    ) -> None:
        self._owner = owner
        self._workspace = workspace
        self._address = address
        self._process_id: str = process_id

    def process_id(self) -> str:
        return self._process_id

    def address(self) -> str:
        return self._address

    def workspace(self) -> str:
        return self._workspace

    def owner(self) -> str:
        return self._owner

    async def stop(self) -> None:
        cmd = await run_command(_docker_stop, self._process_id)

        if cmd.returncode != 0:
            logging.info(
                f"Stopping container {self.process_id} returned exit code {cmd.returncode}"
            )

    def client(self) -> OcrdBrowserClient:
        return HttpBrowserClient(self.address())


class DockerOcrdBrowserFactory:
    def __init__(self, host: str, available_ports: set[int]) -> None:
        self._host = host
        self._ports = available_ports
        self._containers: list[DockerOcrdBrowser] = []

    async def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        abs_workspace = path.abspath(workspace_path)
        port_binding = functools.partial(start_browser, owner, abs_workspace)
        container, _ = await try_bind(port_binding, self._host, self._ports)
        self._containers.append(container)
        return container

    async def stop_all(self) -> None:
        running_ids = [c.process_id() for c in self._containers]
        if running_ids:
            cmd = await run_command(_docker_kill, " ".join(running_ids))
            await cmd.wait()

        self._containers = []


async def start_browser(
    owner: str, workspace: str, host: str, port: int
) -> PortBindingResult[DockerOcrdBrowser]:
    cmd = await run_command(
        _docker_run, container_name(owner, workspace), workspace, port
    )

    return_code = await wait_for(cmd)
    if return_code != 0:
        return PortBindingError()

    container = DockerOcrdBrowser(
        owner, workspace, f"{host}:{port}", await read_container_id(cmd)
    )

    return container


def container_name(owner: str, workspace: str) -> str:
    workspace = path.basename(workspace)
    return f"ocrd-browser-{owner}-{workspace}"


async def wait_for(cmd: asyncio.subprocess.Process) -> int:
    return_code = await cmd.wait()
    await log_from_stream(cmd.stderr)

    return return_code


async def read_container_id(cmd: asyncio.subprocess.Process) -> str:
    stdout = cmd.stdout
    container_id = ""
    if stdout:
        container_id = str(await stdout.read()).strip()

    return container_id


async def log_from_stream(stream: asyncio.StreamReader | None) -> None:
    if not stream:
        return

    logging.info(await stream.read())
