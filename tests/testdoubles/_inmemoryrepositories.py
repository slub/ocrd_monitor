from dataclasses import dataclass, field
from datetime import datetime
from typing import Collection, Callable

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.protocols import BrowserRestoringFactory, OcrdJob
from ._browserspy import BrowserSpy


@dataclass
class BrowserEntry:
    owner: str
    workspace: str
    address: str
    process_id: str
    last_access_time: datetime = field(default_factory=datetime.now, compare=False)

    def restore(self, factory: BrowserRestoringFactory) -> OcrdBrowser:
        return factory(self.owner, self.workspace, self.address, self.process_id)


class InMemoryBrowserProcessRepository:
    def __init__(
        self,
        restoring_factory: BrowserRestoringFactory | None = None,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._processes: list[BrowserEntry] = []
        self.restoring_factory: BrowserRestoringFactory = (
            restoring_factory or BrowserSpy
        )
        self.clock = clock

    async def insert(self, browser: OcrdBrowser) -> None:
        entry = BrowserEntry(
            browser.owner(),
            browser.workspace(),
            browser.address(),
            browser.process_id(),
            self.clock(),
        )

        self._processes.append(entry)

    async def delete(self, browser: OcrdBrowser) -> None:
        entry = BrowserEntry(
            browser.owner(),
            browser.workspace(),
            browser.address(),
            browser.process_id(),
        )

        self._processes.remove(entry)

    async def _find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
    ) -> list[BrowserEntry]:
        def match(browser: BrowserEntry) -> bool:
            matches = True
            if owner is not None:
                matches = matches and browser.owner == owner

            if workspace is not None:
                matches = matches and browser.workspace == workspace

            return matches

        return [b for b in self._processes if match(b)]

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
    ) -> Collection[OcrdBrowser]:
        return [
            entry.restore(self.restoring_factory)
            for entry in await self._find(owner=owner, workspace=workspace)
        ]

    async def _first(self, *, owner: str, workspace: str) -> BrowserEntry | None:
        results = await self._find(owner=owner, workspace=workspace)
        return next(iter(results), None)

    async def first(self, *, owner: str, workspace: str) -> OcrdBrowser | None:
        entry = await self._first(owner=owner, workspace=workspace)
        if entry is None:
            return None

        entry.last_access_time = self.clock()
        return entry.restore(self.restoring_factory)

    async def last_access_time_for(self, browser: OcrdBrowser) -> datetime | None:
        entry = await self._first(owner=browser.owner(), workspace=browser.workspace())

        if entry is None:
            return None

        return entry.last_access_time

    async def browsers_by_access_time(self) -> list[tuple[OcrdBrowser, datetime]]:
        entries = sorted(await self._find(), key=lambda b: b.last_access_time)
        return [
            (e.restore(self.restoring_factory), e.last_access_time) for e in entries
        ]

    async def count(self) -> int:
        return len(self._processes)


class InMemoryJobRepository:
    def __init__(self, jobs: list[OcrdJob] | None = None) -> None:
        self._jobs = jobs or []

    async def insert(self, job: OcrdJob) -> None:
        self._jobs.append(job)

    async def find_all(self) -> list[OcrdJob]:
        return list(self._jobs)
