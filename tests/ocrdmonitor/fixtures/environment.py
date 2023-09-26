from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime
from types import TracebackType
from typing import AsyncContextManager, Callable, Self, Type

from fastapi.testclient import TestClient

from ocrdbrowser import OcrdBrowserFactory
from ocrdmonitor.processstatus import ProcessStatus
from ocrdmonitor.protocols import (
    BrowserProcessRepository,
    BrowserRestoringFactory,
    RemoteServer,
    Repositories,
)
from ocrdmonitor.server.app import create_app
from ocrdmonitor.server.settings import Settings
from tests.ocrdmonitor.fixtures.repository import inmemory_repository
from tests.ocrdmonitor.fixtures.settings import create_settings
from tests.testdoubles import (
    BrowserRegistry,
    BrowserSpy,
    BrowserTestDouble,
    BrowserTestDoubleFactory,
    IteratingBrowserTestDoubleFactory,
    RegistryBrowserFactory,
    RestoringRegistryBrowserFactory,
)


class RemoteDummy:
    async def read_file(self, path: str) -> str:
        return ""

    async def process_status(self, process_group: int) -> list[ProcessStatus]:
        return []


@dataclass
class DevEnvironment:
    settings: Settings
    _repositories: Repositories
    _factory: BrowserTestDoubleFactory
    controller_remote: RemoteServer = RemoteDummy()

    _app: TestClient = field(init=False)

    def __post_init__(self) -> None:
        self._app = TestClient(create_app(self))

    async def repositories(self) -> Repositories:
        return self._repositories

    def browser_factory(self) -> OcrdBrowserFactory:
        return self._factory

    def controller_server(self) -> RemoteServer:
        return self.controller_remote

    @property
    def app(self) -> TestClient:
        return self._app


BrowserConstructor = Callable[[], BrowserTestDouble]

Clock = Callable[[], datetime]
RepositoryInitializer = Callable[
    [BrowserRestoringFactory, Clock],
    AsyncContextManager[Repositories],
]


class Fixture:
    def __init__(self) -> None:
        self.browser_constructor: BrowserConstructor = BrowserSpy
        self.repo_constructor: RepositoryInitializer = inmemory_repository
        self.remote_controller: RemoteServer = RemoteDummy()
        self.existing_browsers: list[BrowserTestDouble] = []
        self.session_id = ""
        self.clock = lambda: datetime.now()

        self._ctxstack = AsyncExitStack()

    def with_clock(self, clock: Clock) -> Self:
        self.clock = clock
        return self

    def with_browser_type(self, browser_constructor: BrowserConstructor) -> Self:
        self.browser_constructor = browser_constructor
        return self

    def with_repository_type(self, repo_constructor: RepositoryInitializer) -> Self:
        self.repo_constructor = repo_constructor
        return self

    def with_running_browsers(self, *browsers: BrowserTestDouble) -> Self:
        self.existing_browsers = list(browsers)
        return self

    def with_controller_remote(self, remote: RemoteServer) -> Self:
        self.remote_controller = remote
        return self

    def with_session_id(self, session_id: str) -> Self:
        self.session_id = session_id
        return self

    async def __aenter__(self) -> DevEnvironment:
        registry = BrowserRegistry()
        repositories = await self._init_repos(registry)
        factory = await self._create_factory(registry)
        await self._insert_running_browsers(registry, repositories.browser_processes)

        env = DevEnvironment(
            create_settings(),
            _factory=factory,
            _repositories=repositories,
            controller_remote=self.remote_controller,
        )

        self._init_app(env.app)
        return env

    async def _init_repos(self, registry: BrowserRegistry) -> Repositories:
        restoring_factory = RestoringRegistryBrowserFactory(registry)
        return await self._ctxstack.enter_async_context(
            self.repo_constructor(restoring_factory, self.clock)
        )

    async def _create_factory(
        self, registry: BrowserRegistry
    ) -> BrowserTestDoubleFactory:
        factory = IteratingBrowserTestDoubleFactory(
            default_browser=self.browser_constructor
        )
        creating_factory = RegistryBrowserFactory(factory, registry)
        return await self._ctxstack.enter_async_context(creating_factory)

    def _init_app(self, app: TestClient) -> TestClient:
        self._ctxstack.enter_context(app)
        if self.session_id:
            app.cookies["session_id"] = self.session_id
        return app

    async def _insert_running_browsers(
        self, registry: BrowserRegistry, repository: BrowserProcessRepository
    ) -> None:
        for browser in self.existing_browsers:
            registry.insert(browser)
            await repository.insert(browser)
            await browser.start()

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._ctxstack.aclose()
