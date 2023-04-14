from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Protocol
from ocrdmonitor import sshremote

from ocrdmonitor.ocrdjob import OcrdJob
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
    def __init__(self, remote: RemoteServer, job_dir: Path) -> None:
        self._remote = remote
        self._job_dir = job_dir
        logging.info(f"process_query: {remote}")
        logging.info(f"job_dir: {job_dir}")

    def get_jobs(self) -> list[OcrdJob]:
        def is_ocrd_job(j: OcrdJob | None) -> TypeGuard[OcrdJob]:
            return j is not None

        job_candidates = [
            self._try_parse(job_file)
            for job_file in self._job_dir.iterdir()
            if job_file.is_file()
        ]

        return list(filter(is_ocrd_job, job_candidates))

    def _try_parse(self, job_file: Path) -> OcrdJob | None:
        job_str = job_file.read_text()
        try:
            return OcrdJob.from_str(job_str)
        except (ValueError, KeyError) as e:
            logging.warning(f"found invalid job file: {job_file.name} - {e}")
            return None

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
