from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Collection, NamedTuple, Protocol

from ocrdbrowser import OcrdBrowser, OcrdBrowserFactory
from ocrdmonitor.processstatus import ProcessStatus
from ocrdmonitor.server.settings import Settings


class BrowserRestoringFactory(Protocol):
    def __call__(
        self, owner: str, workspace: str, address: str, process_id: str
    ) -> OcrdBrowser:
        ...


class BrowserProcessRepository(Protocol):
    async def insert(self, browser: OcrdBrowser) -> None:
        ...

    async def delete(self, browser: OcrdBrowser) -> None:
        ...

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
    ) -> Collection[OcrdBrowser]:
        ...

    async def first(self, *, owner: str, workspace: str) -> OcrdBrowser | None:
        ...

    async def count(self) -> int:
        ...


@dataclass(frozen=True)
class OcrdJob:
    pid: int | None
    return_code: int | None
    time_created: datetime
    time_terminated: datetime
    process_id: str
    task_id: str
    process_dir: Path
    workdir: Path
    remotedir: str
    workflow_file: Path
    controller_address: str

    @property
    def is_running(self) -> bool:
        return self.pid is not None

    @property
    def is_completed(self) -> bool:
        return self.return_code is not None

    @property
    def workflow(self) -> str:
        return Path(self.workflow_file).name


class JobRepository(Protocol):
    async def insert(self, job: OcrdJob) -> None:
        ...

    async def find_all(self) -> list[OcrdJob]:
        ...
 
class OcrdWorkflowStatus(Enum):
    PUBLISHED = 1
    DRAFT = 2
    TRASH = 3

@dataclass(frozen=True)
class OcrdWorkflow:
    name: str
    file: Path
    status: OcrdWorkflowStatus

    @property
    def workflow(self) -> str:
        return Path(self.workflow_file).name


class WorkflowRepository(Protocol):
    async def insert(self, workflow: OcrdWorkflow) -> None:
        ...

    async def find_all(self) -> list[OcrdWorkflow]:
        ...


class RemoteServer(Protocol):
    async def read_file(self, path: str) -> str:
        ...

    async def process_status(self, process_group: int) -> list[ProcessStatus]:
        ...


class Repositories(NamedTuple):
    browser_processes: BrowserProcessRepository
    ocrd_jobs: JobRepository


class Environment(Protocol):
    settings: Settings

    async def repositories(self) -> Repositories:
        ...

    def browser_factory(self) -> OcrdBrowserFactory:
        ...

    def controller_server(self) -> RemoteServer:
        ...
