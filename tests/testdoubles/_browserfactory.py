import asyncio
from types import TracebackType
from typing import Callable, Protocol, Self, Type

from ocrdbrowser import OcrdBrowser
from ._browserspy import BrowserSpy


class BrowserTestDouble(OcrdBrowser, Protocol):
    def set_owner_and_workspace(self, owner: str, workspace: str) -> None:
        ...

    @property
    def is_running(self) -> bool:
        ...


class SingletonBrowserTestDoubleFactory:
    def __init__(self, browser: BrowserTestDouble | None = None) -> None:
        self._browser = browser or BrowserSpy()

    def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        self._browser.set_owner_and_workspace(owner, workspace_path)
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

    def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        browser = next(self._proc_iter, self._default_browser())
        browser.set_owner_and_workspace(owner, workspace_path)
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
