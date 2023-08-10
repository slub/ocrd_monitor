from typing import Collection, NamedTuple

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.protocols import BrowserRestoringFactory, OcrdJob

from ._browserspy import BrowserSpy


class BrowserEntry(NamedTuple):
    owner: str
    workspace: str
    address: str
    process_id: str


class InMemoryBrowserProcessRepository:
    def __init__(
        self, restoring_factory: BrowserRestoringFactory | None = None
    ) -> None:
        self._processes: list[BrowserEntry] = []
        self.restoring_factory: BrowserRestoringFactory = (
            restoring_factory or BrowserSpy
        )

    async def insert(self, browser: OcrdBrowser) -> None:
        entry = BrowserEntry(
            browser.owner(),
            browser.workspace(),
            browser.address(),
            browser.process_id(),
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

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
    ) -> Collection[OcrdBrowser]:
        def match(browser: BrowserEntry) -> bool:
            matches = True
            if owner is not None:
                matches = matches and browser.owner == owner

            if workspace is not None:
                matches = matches and browser.workspace == workspace

            return matches

        return [
            self.restoring_factory(
                process_id=browser.process_id,
                owner=browser.owner,
                workspace=browser.workspace,
                address=browser.address,
            )
            for browser in self._processes
            if match(browser)
        ]

    async def first(self, *, owner: str, workspace: str) -> OcrdBrowser | None:
        results = await self.find(owner=owner, workspace=workspace)
        return next(iter(results), None)

    async def count(self) -> int:
        return len(self._processes)


class InMemoryJobRepository:
    def __init__(self, jobs: list[OcrdJob] | None = None) -> None:
        self._jobs = jobs or []

    async def insert(self, job: OcrdJob) -> None:
        self._jobs.append(job)

    async def find_all(self) -> list[OcrdJob]:
        return list(self._jobs)
