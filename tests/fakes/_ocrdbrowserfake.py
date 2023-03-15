from types import TracebackType
from typing import AsyncContextManager, Type

from ocrdbrowser import Channel, OcrdBrowser
from ocrdbrowser._websocketchannel import WebSocketChannel

from ._backgroundprocess import BackgroundProcess
from ._broadwayfake import broadway_fake


class BrowserFake:
    def __init__(self, owner: str = "", workspace: str = "") -> None:
        self._owner: str = owner
        self._workspace: str = workspace
        self._browser = broadway_fake(workspace)
        self._running = False

    def set_owner_and_workspace(self, owner: str, workspace: str) -> None:
        self._owner = owner
        self._workspace = workspace
        self._browser = broadway_fake(workspace)

    def address(self) -> str:
        return "http://localhost:7000"

    def owner(self) -> str:
        return self._owner

    def workspace(self) -> str:
        return self._workspace

    def start(self) -> None:
        self._running = True
        self._browser.launch()

    def stop(self) -> None:
        self._running = False
        self._browser.shutdown()

    def open_channel(self) -> AsyncContextManager[Channel]:
        return WebSocketChannel(self.address() + "/socket")

    @property
    def broadway_server(self) -> BackgroundProcess:
        return self._browser

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_server_running(self) -> bool:
        return self._browser.is_running


class BrowserFakeFactory:
    def __init__(self, *browsers: BrowserFake) -> None:
        self._browsers = set(browsers)
        self._browser_iter = iter(self._browsers)

    def __enter__(self) -> "BrowserFakeFactory":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        for browser in self._browsers:
            browser.stop()

    def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        browser = next(self._browser_iter, BrowserFake(owner, workspace_path))
        self._browsers.add(browser)
        return browser
