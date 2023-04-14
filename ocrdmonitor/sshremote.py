from __future__ import annotations

import asyncio
import logging
import shlex
from pathlib import Path
from typing import Protocol

from ocrdmonitor.processstatus import ProcessStatus


class SSHConfig(Protocol):
    host: str
    port: int
    user: str
    keyfile: Path


class SSHRemote:
    def __init__(self, config: SSHConfig) -> None:
        self._config = config

    async def read_file(self, path: str) -> str:
        result = await asyncio.create_subprocess_shell(
            _ssh(self._config, f"cat {path}"),
            stdout=asyncio.subprocess.PIPE,
        )
        await result.wait()

        if not result.stdout:
            return ""

        return (await result.stdout.read()).decode()

    async def process_status(self, process_group: int) -> list[ProcessStatus]:
        pid_cmd = ProcessStatus.shell_command(process_group)
        result = await asyncio.create_subprocess_shell(
            _ssh(self._config, pid_cmd),
            stdout=asyncio.subprocess.PIPE,
        )

        if await result.wait() > 0:
            logging.error(
                f"checking status of process {process_group} failed: {result.stderr}"
            )
            return []

        if not result.stdout:
            return []

        output = (await result.stdout.read()).decode()
        return ProcessStatus.from_shell_output(output)


def _ssh(config: SSHConfig, cmd: str) -> str:
    return shlex.join(
        (
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            str(config.keyfile),
            "-p",
            str(config.port),
            f"{config.user}@{config.host}",
            *shlex.split(cmd),
        )
    )
