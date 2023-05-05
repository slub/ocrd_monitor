from typing import Collection
from ocrdmonitor.browserprocess import BrowserProcess


class InMemoryBrowserProcessRepository:
    def __init__(self) -> None:
        self._processes: list[BrowserProcess] = []

    async def insert(self, browser: BrowserProcess) -> None:
        self._processes.append(browser)

    async def delete(self, browser: BrowserProcess) -> None:
        self._processes.remove(browser)

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
        process_id: str | None = None,
    ) -> Collection[BrowserProcess]:
        def match(browser: BrowserProcess) -> bool:
            matches = True
            if owner is not None:
                matches = matches and browser.owner() == owner

            if workspace is not None:
                matches = matches and browser.workspace() == workspace

            if process_id is not None:
                matches = matches and browser.process_id() == process_id

            return matches

        return list(filter(match, self._processes))
