from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Protocol

from ocrdmonitor.processstatus import PS_CMD, ProcessStatus


class SSHConfig(Protocol):
    host: str
    port: int
    user: str
    keyfile: Path


_SSH = (
    "ssh -o StrictHostKeyChecking=no -i '{keyfile}' -p {port} {user}@{host} '{ps_cmd}'"
)


def process_status(config: SSHConfig, remotedir: str) -> list[ProcessStatus]:
    ssh_cmd = _build_ssh_command(config, remotedir)

    result = subprocess.run(
        ssh_cmd,
        shell=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode > 0:
        logging.error(
            f"checking status of process for {remotedir} failed: {result.stderr}"
        )
    return ProcessStatus.from_ps_output(result.stdout)


def _build_ssh_command(config: SSHConfig, remotedir: str) -> str:
    ps_cmd = PS_CMD.format(remotedir)
    return _SSH.format(
        port=config.port,
        keyfile=config.keyfile,
        user=config.user,
        host=config.host,
        ps_cmd=ps_cmd,
    )
