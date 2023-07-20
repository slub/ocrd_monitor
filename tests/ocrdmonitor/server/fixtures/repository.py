from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import patch

from testcontainers.mongodb import MongoDbContainer

import ocrdmonitor.database as database
import ocrdmonitor.database._browserprocessrepository
from ocrdmonitor.repositories import BrowserProcessRepository, BrowserRestoringFactory
from ocrdmonitor.server.settings import OcrdBrowserSettings
from tests.testdoubles import InMemoryBrowserProcessRepository


@asynccontextmanager
async def mongodb_repository(
    restoring_factory: BrowserRestoringFactory,
) -> AsyncIterator[
    ocrdmonitor.database._browserprocessrepository.MongoBrowserProcessRepository
]:
    with MongoDbContainer() as container:
        await database.init(container.get_connection_url(), force_initialize=True)
        yield ocrdmonitor.database._browserprocessrepository.MongoBrowserProcessRepository(
            restoring_factory
        )


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
