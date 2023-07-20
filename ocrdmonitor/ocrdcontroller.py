from __future__ import annotations

from typing import Protocol

from ocrdmonitor.processstatus import ProcessState, ProcessStatus
from ocrdmonitor.repositories import JobRepository, OcrdJob


class RemoteServer(Protocol):
    async def read_file(self, path: str) -> str:
        ...

    async def process_status(self, process_group: int) -> list[ProcessStatus]:
        ...


class OcrdController:
    def __init__(self, remote: RemoteServer, job_repository: JobRepository) -> None:
        self._remote = remote
        self._job_repository = job_repository

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
