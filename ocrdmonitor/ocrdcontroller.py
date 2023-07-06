from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Protocol
from ocrdmonitor.server.settings import OcrdControllerSettings
from ocrdmonitor.sshremote import SSHRemote

#from ocrdmonitor.ocrdjob import OcrdJob
from ocrdmonitor.dbmodel import OcrdJob
from ocrdmonitor.processstatus import ProcessStatus, ProcessState

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

class RemoteServer(Protocol):
    async def read_file(self, path: str) -> str:
        ...

    async def process_status(self, process_group: int) -> list[ProcessStatus]:
        ...


class OcrdController:
    def __init__(self, settings: OcrdControllerSettings) -> None:
        self._remote : RemoteServer = SSHRemote(settings)
        logging.info(f"process_query: {self._remote}")

    async def get_jobs(self) -> list[OcrdJob]:
        jobs = await OcrdJob.find_all().to_list()
        return jobs

    async def status_for(self, ocrd_job: OcrdJob) -> ProcessStatus | None:
        if ocrd_job.remotedir is None:
            return None

        pid = await self._remote.read_file(f"/data/{ocrd_job.remotedir}/ocrd.pid")
        process_statuses = await self._remote.process_status(int(pid))

        for status in process_statuses:
            if status.state == ProcessState.RUNNING:
                return status

        if process_statuses:
            return process_statuses[0]

        return None
