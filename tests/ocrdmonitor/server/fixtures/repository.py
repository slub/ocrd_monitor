from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import patch

from testcontainers.mongodb import MongoDbContainer

from ocrdmonitor import dbmodel
from ocrdmonitor.browserprocess import BrowserProcessRepository, BrowserRestoringFactory
from ocrdmonitor.server.settings import OcrdBrowserSettings
from tests.testdoubles import InMemoryBrowserProcessRepository


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


@asynccontextmanager
async def patch_repository(repository: BrowserProcessRepository) -> AsyncIterator[None]:
    async def _repository(_: OcrdBrowserSettings) -> BrowserProcessRepository:
        return repository

    with patch.object(OcrdBrowserSettings, "repository", _repository):
        yield
