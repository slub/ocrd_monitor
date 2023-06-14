from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncIterator, Callable
from unittest.mock import patch

import pytest
import pytest_asyncio
from testcontainers.mongodb import MongoDbContainer

from ocrdbrowser import OcrdBrowser
from ocrdmonitor import dbmodel
from ocrdmonitor.browserprocess import BrowserProcessRepository, BrowserRestoringFactory
from ocrdmonitor.server.settings import OcrdBrowserSettings
from tests.testdoubles import (
    BrowserSpy,
    InMemoryBrowserProcessRepository,
)
from tests.testdoubles._browserfactory import SingletonRestoringBrowserFactory


RepositoryInitializer = Callable[
    [BrowserRestoringFactory],
    AsyncContextManager[BrowserProcessRepository],
]


@asynccontextmanager
async def mongodb_repository(
    restoring_factory: BrowserRestoringFactory,
) -> AsyncIterator[dbmodel.MongoBrowserProcessRepository]:
    with MongoDbContainer() as container:
        await dbmodel.init(container.get_connection_url(), force_initialize=True)
        yield dbmodel.MongoBrowserProcessRepository(restoring_factory)


@asynccontextmanager
async def inmemory_repository(
    restoring_factory: BrowserRestoringFactory,
) -> AsyncIterator[InMemoryBrowserProcessRepository]:
    yield InMemoryBrowserProcessRepository(restoring_factory)


def spy_restoring_factory() -> BrowserRestoringFactory:
    def factory(
        owner: str, workspace: str, address: str, process_id: str
    ) -> OcrdBrowser:
        return BrowserSpy(owner, workspace, address, process_id, running=True)

    return factory


@asynccontextmanager
async def patch_repository(repository: BrowserProcessRepository) -> AsyncIterator[None]:
    async def _repository(_: OcrdBrowserSettings) -> BrowserProcessRepository:
        return repository

    with patch.object(OcrdBrowserSettings, "repository", _repository):
        yield


@pytest_asyncio.fixture(
    autouse=True,
    params=[
        inmemory_repository,
        pytest.param(
            mongodb_repository,
            marks=(pytest.mark.integration, pytest.mark.needs_docker),
        ),
    ],
)
async def auto_repository(
    request: pytest.FixtureRequest,
) -> AsyncIterator[BrowserProcessRepository] | None:
    """
    This fixture will be used automatically for all tests,
    as a repository for browser processes is pretty much always needed.

    It can be turned off by marking a test with 'pytest.mark.no_auto_repository'
    """
    if "no_auto_repository" in request.keywords:
        # NOTE: we're yielding 0 here, because pytest_asyncio
        # raises a StopIterationError if we return or yield None
        yield 0
    else:
        repository_constructor: RepositoryInitializer = request.param
        async with repository_constructor(spy_restoring_factory()) as repository:
            async with patch_repository(repository):
                yield repository


@pytest_asyncio.fixture
async def singleton_restoring_factory() -> AsyncIterator[
    SingletonRestoringBrowserFactory
]:
    async with SingletonRestoringBrowserFactory() as factory:
        yield factory
