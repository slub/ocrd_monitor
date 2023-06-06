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
        cmd = await _run_command(_docker_stop, self._process_id)

        if cmd.returncode != 0:
            logging.info(
                f"Stopping container {self.process_id} returned exit code {cmd.returncode}"
            )

    def client(self) -> OcrdBrowserClient:
        return HttpBrowserClient(self.address())


def _container_name(owner: str, workspace: str) -> str:
    workspace = path.basename(workspace)
    return f"ocrd-browser-{owner}-{workspace}"


class DockerOcrdBrowserFactory:
    def __init__(self, host: str, available_ports: set[int]) -> None:
        self._host = host
        self._ports = available_ports
        self._containers: list[DockerOcrdBrowser] = []

    async def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        abs_workspace = path.abspath(workspace_path)
        port = Port(self._ports)

        cmd = await _run_command(
            _docker_run,
            _container_name(owner, abs_workspace),
            abs_workspace,
            port.get(),
        )

        stdout = cmd.stdout
        container_id = ""
        if stdout:
            container_id = str(await stdout.read()).strip()

        container = DockerOcrdBrowser(
            owner,
            abs_workspace,
            f"{self._host}:{port.get()}",
            container_id,
        )

        self._containers.append(container)
        return container

    async def stop_all(self) -> None:
        running_ids = [c.process_id() for c in self._containers]
        if running_ids:
            await _run_command(_docker_kill, " ".join(running_ids))

        self._containers = []
