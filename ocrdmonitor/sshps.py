from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Protocol

from ocrdmonitor.processstatus import ProcessStatus


class SSHConfig(Protocol):
    host: str
    port: int
    user: str
    keyfile: Path

def process_status(config: SSHConfig, remotedir: str) -> list[ProcessStatus]:
    pid_cmd = ProcessStatus.remotedir_to_pid_cmd(remotedir)
    pid_cmd = _build_ssh_command(config, pid_cmd)
    result = subprocess.run(
        pid_cmd,
        shell=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode > 0:
        logging.error(
            f"looking up PID of process for {remotedir} failed: {result.stderr}"
        )
        return []
    pid = result.stdout.strip()
    ps_cmd = ProcessStatus.session_pid_to_ps_cmd(pid)
    ps_cmd = _build_ssh_command(config, ps_cmd)
    result = subprocess.run(
        ps_cmd,
        shell=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode > 0:
        logging.error(
            f"checking status of process {pid} failed: {result.stderr}"
        )
        return []
    return ProcessStatus.from_ps_output(result.stdout)

def _build_ssh_command(config: SSHConfig, cmd: str) -> str:
    return "ssh -o StrictHostKeyChecking=no -i '{keyfile}' -p {port} {user}@{host} '{cmd}'".format(
        port=config.port,
        keyfile=config.keyfile,
        user=config.user,
        host=config.host,
        cmd=cmd,
    )
