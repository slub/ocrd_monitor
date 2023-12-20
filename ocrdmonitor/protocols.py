from datetime import datetime
from pathlib import Path
from typing import Collection, NamedTuple, Protocol

from ocrdbrowser import OcrdBrowser, OcrdBrowserFactory
from ocrdmonitor.processstatus import ProcessStatus
from ocrdmonitor.server.settings import Settings

from pydantic import BaseModel, computed_field

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


class OcrdJob(BaseModel):
    id: str
    pid: int | None
    return_code: int | None
    time_created: datetime
    time_terminated: datetime | None
    process_id: str
    task_id: str
    process_dir: Path
    workdir: Path
    remotedir: str
    workflow_file: Path
    controller_address: str

    @property
    def is_processing(self) -> bool:
        return self.pid is not None

    @property
    def is_completed(self) -> bool:
        return self.return_code is not None

    @computed_field   
    @property
    def workflow(self) -> str:
        return Path(self.workflow_file).name
    
    @computed_field   
    @property
    def workspace(self) -> str:
        return Path(self.process_dir).name

    @computed_field   
    @property
    def status(self) -> str:
        if self.is_processing :
            return "PROCESSING"
        if self.is_completed :
            if self.return_code == 0 :
                return "SUCCESS"
            else : 
                return "FAILURE"
        return "UNDEFINED"


class JobRepository(Protocol):
    async def insert(self, job: OcrdJob) -> None:
        ...

    async def find_one(self) -> list[OcrdJob]:
        ...

    async def get(self) -> OcrdJob:
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
