from contextlib import asynccontextmanager
from typing import AsyncIterator

from testcontainers.mongodb import MongoDbContainer

import ocrdmonitor.database as database
from ocrdmonitor.protocols import BrowserRestoringFactory, Repositories
from tests.testdoubles import InMemoryBrowserProcessRepository, InMemoryJobRepository


@asynccontextmanager
async def mongodb_repository(
    restoring_factory: BrowserRestoringFactory,
) -> AsyncIterator[Repositories]:
    with MongoDbContainer() as container:
        await database.init(container.get_connection_url(), force_initialize=True)
        yield Repositories(
            database.MongoBrowserProcessRepository(restoring_factory),
            database.MongoJobRepository(),
        )


@asynccontextmanager
async def inmemory_repository(
    restoring_factory: BrowserRestoringFactory,
) -> AsyncIterator[Repositories]:
    yield Repositories(
        InMemoryBrowserProcessRepository(restoring_factory), InMemoryJobRepository()
    )
