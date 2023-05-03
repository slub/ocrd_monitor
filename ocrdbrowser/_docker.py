from __future__ import annotations

import asyncio
import logging
import os.path as path
from typing import Any

from ._browser import OcrdBrowser, OcrdBrowserClient
from ._port import Port
from ._client import HttpBrowserClient

_docker_run = "docker run --rm -d --name {} -v {}:/data -p {}:8085 ocrd-browser:latest"
_docker_stop = "docker stop {}"
_docker_kill = "docker kill {}"


async def _run_command(cmd: str, *args: Any) -> asyncio.subprocess.Process:
    command = cmd.format(*args)
    return await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
    )


class DockerOcrdBrowser:
    def __init__(self, host: str, port: Port, owner: str, workspace: str) -> None:
        self._host = host
        self._port = port
        self._owner = owner
        self._workspace = path.abspath(workspace)
        self.id: str | None = None

    def process_id(self) -> str:
        return self._container_name()

    def address(self) -> str:
        return f"{self._host}:{self._port}"

    def workspace(self) -> str:
        return self._workspace

    def owner(self) -> str:
        return self._owner

    async def start(self) -> None:
        cmd = await _run_command(
            _docker_run, self._container_name(), self._workspace, self._port.get()
        )
        self.id = str(cmd.stdout).strip()

    async def stop(self) -> None:
        cmd = await _run_command(
            _docker_stop, self._container_name(), self.workspace(), self._port.get()
        )

        if cmd.returncode != 0:
            logging.info(
                f"Stopping container {self.id} returned exit code {cmd.returncode}"
            )

        self._port.release()
        self.id = None

    def client(self) -> OcrdBrowserClient:
        return HttpBrowserClient(self.address())

    def _container_name(self) -> str:
        workspace = path.basename(self.workspace())
        return f"ocrd-browser-{self.owner()}-{workspace}"


class DockerOcrdBrowserFactory:
    def __init__(self, host: str, available_ports: set[int]) -> None:
        self._host = host
        self._ports = available_ports
        self._containers: list[DockerOcrdBrowser] = []

    def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        container = DockerOcrdBrowser(
            self._host, Port(self._ports), owner, workspace_path
        )
        self._containers.append(container)
        return container

    async def stop_all(self) -> None:
        running_ids = [c.id for c in self._containers if c.id]
        if running_ids:
            await _run_command(_docker_kill, " ".join(running_ids))

        self._containers = []
