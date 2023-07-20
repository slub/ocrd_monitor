from dataclasses import dataclass
from types import TracebackType
from typing import (
    Any,
    AsyncContextManager,
    Callable,
    ContextManager,
    Self,
    Type,
)

from fastapi.testclient import TestClient

from ocrdmonitor.repositories import BrowserProcessRepository, BrowserRestoringFactory
from ocrdmonitor.server.app import create_app
from tests.ocrdmonitor.server.fixtures.factory import patch_factory
from tests.ocrdmonitor.server.fixtures.repository import (
    inmemory_repository,
    patch_repository,
)
from tests.ocrdmonitor.server.fixtures.settings import create_settings
from tests.testdoubles import (
    BrowserRegistry,
    BrowserSpy,
    BrowserTestDouble,
    IteratingBrowserTestDoubleFactory,
    RegistryBrowserFactory,
    RestoringRegistryBrowserFactory,
)


@dataclass
class Environment:
    repository: BrowserProcessRepository
    app: TestClient


BrowserConstructor = Callable[[], BrowserTestDouble]
RepositoryInitializer = Callable[
    [BrowserRestoringFactory],
    AsyncContextManager[BrowserProcessRepository],
]


class Fixture:
    def __init__(self) -> None:
        self.browser_constructor: BrowserConstructor = BrowserSpy
        self.repo_constructor: RepositoryInitializer = inmemory_repository
        self.existing_browsers: list[BrowserTestDouble] = []
        self.session_id = ""

        self._open_contexts: list[ContextManager[Any] | AsyncContextManager[Any]] = []

    def with_browser_type(self, browser_constructor: BrowserConstructor) -> Self:
        self.browser_constructor = browser_constructor
        return self

    def with_repository_type(self, repo_constructor: RepositoryInitializer) -> Self:
        self.repo_constructor = repo_constructor
        return self

    def with_running_browsers(self, *browsers: BrowserTestDouble) -> Self:
        self.existing_browsers = list(browsers)
        return self

    def with_session_id(self, session_id: str) -> Self:
        self.session_id = session_id
        return self

    async def __aenter__(self) -> Environment:
        registry = BrowserRegistry({})
        repository = await self._patch_repository(registry)
        await self._patch_factory(registry)
        await self._insert_running_browsers(registry, repository)
        app = self._build_app()

        return Environment(repository=repository, app=app)

    async def _patch_repository(
        self, registry: BrowserRegistry
    ) -> BrowserProcessRepository:
        repository = await self._init_repo(registry)
        patcher = patch_repository(repository)
        self._open_contexts.append(patcher)
        await patcher.__aenter__()
        return repository

    async def _init_repo(self, registry: BrowserRegistry) -> BrowserProcessRepository:
        restoring_factory = RestoringRegistryBrowserFactory(registry)
        repo_ctx = self.repo_constructor(restoring_factory)
        self._open_contexts.append(repo_ctx)
        repository = await repo_ctx.__aenter__()
        return repository

    async def _patch_factory(self, registry: BrowserRegistry) -> None:
        creating_factory = RegistryBrowserFactory(
            IteratingBrowserTestDoubleFactory(default_browser=self.browser_constructor),
            registry,
        )
        patcher = patch_factory(creating_factory)
        await patcher.__aenter__()
        self._open_contexts.append(patcher)

    def _build_app(self) -> TestClient:
        app = TestClient(create_app(create_settings()))
        app.__enter__()
        if self.session_id:
            app.cookies["session_id"] = self.session_id

        self._open_contexts.append(app)
        return app

    async def _insert_running_browsers(
        self, registry: BrowserRegistry, repository: BrowserProcessRepository
    ) -> None:
        for browser in self.existing_browsers:
            registry[browser.address()] = browser
            await repository.insert(browser)
            await browser.start()

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        for ctx in self._open_contexts:
            if isinstance(ctx, AsyncContextManager):
                await ctx.__aexit__(exc_type, exc_value, traceback)
            else:
                ctx.__exit__(exc_type, exc_value, traceback)
