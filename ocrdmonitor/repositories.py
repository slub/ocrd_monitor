from datetime import datetime
from pathlib import Path
from typing import Collection, NamedTuple, Protocol
from ocrdbrowser import OcrdBrowser


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


class OcrdJob(NamedTuple):
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
    async def find_all(self) -> list[OcrdJob]:
        ...
