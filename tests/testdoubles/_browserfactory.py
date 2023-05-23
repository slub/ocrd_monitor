import asyncio
from types import TracebackType
from typing import Any, Callable, Protocol, Self, Type

from ocrdbrowser import OcrdBrowser
from ._browserspy import BrowserSpy


class BrowserTestDouble(OcrdBrowser, Protocol):
    def set_owner_and_workspace(self, owner: str, workspace: str) -> None:
        ...

    async def start(self) -> None:
        ...

    @property
    def is_running(self) -> bool:
        ...


class SingletonBrowserTestDoubleFactory:
    def __init__(self, browser: BrowserTestDouble | None = None) -> None:
        self._browser = browser or BrowserSpy()

    async def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        self._browser.set_owner_and_workspace(owner, workspace_path)
        await self._browser.start()
        return self._browser

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._browser.stop()


class IteratingBrowserTestDoubleFactory:
    def __init__(
        self,
        *processes: BrowserTestDouble,
        default_browser: Callable[[], BrowserTestDouble] = BrowserSpy,
    ) -> None:
        self._processes = list(processes)
        self._default_browser = default_browser
        self._proc_iter = iter(self._processes)
        self._created: list[BrowserTestDouble] = []

    def add(self, process: BrowserTestDouble) -> None:
        self._processes.append(process)

    async def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        browser = next(self._proc_iter, self._default_browser())
        browser.set_owner_and_workspace(owner, workspace_path)
        await browser.start()
        self._created.append(browser)
        return browser

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        async with asyncio.TaskGroup() as group:
            for browser in self._created:
                group.create_task(browser.stop())


BrowserTestDoubleFactory = (
    SingletonBrowserTestDoubleFactory | IteratingBrowserTestDoubleFactory
)


class SingletonRestoringBrowserFactory:
    def __init__(self) -> None:
        self.browser = BrowserSpy()

    async def __aenter__(self) -> "SingletonRestoringBrowserFactory":
        await self.browser.start()
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.browser.stop()

    def __call__(
        self, owner: str, workspace: str, address: str, process_id: str
    ) -> OcrdBrowser:
        self.browser.set_owner_and_workspace(owner, workspace)
        self.browser._address = address
        self.browser._process_id = process_id
        return self.browser
