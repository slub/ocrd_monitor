from typing import Collection
from ocrdbrowser import OcrdBrowser
from ocrdmonitor.browserprocess import BrowserRestoringFactory
from tests.testdoubles import BrowserSpy


class InMemoryBrowserProcessRepository:
    def __init__(
        self, restoring_factory: BrowserRestoringFactory | None = None
    ) -> None:
        self._processes: list[OcrdBrowser] = []
        self.restoring_factory: BrowserRestoringFactory = (
            restoring_factory or BrowserSpy
        )

    async def insert(self, browser: OcrdBrowser) -> None:
        self._processes.append(browser)

    async def delete(self, browser: OcrdBrowser) -> None:
        self._processes.remove(browser)

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
    ) -> Collection[OcrdBrowser]:
        def match(browser: OcrdBrowser) -> bool:
            matches = True
            if owner is not None:
                matches = matches and browser.owner() == owner

            if workspace is not None:
                matches = matches and browser.workspace() == workspace

            return matches

        return [
            self.restoring_factory(
                process_id=browser.process_id(),
                owner=browser.owner(),
                workspace=browser.workspace(),
                address=browser.address(),
            )
            for browser in self._processes
            if match(browser)
        ]
