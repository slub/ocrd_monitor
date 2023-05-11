import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
)
from unittest.mock import patch

import pytest
import pytest_asyncio
import uvicorn
from fastapi.testclient import TestClient
from testcontainers.mongodb import MongoDbContainer

from ocrdbrowser import OcrdBrowser
from ocrdmonitor import dbmodel
from ocrdmonitor.browserprocess import BrowserProcessRepository, BrowserRestoringFactory
from ocrdmonitor.server.app import create_app
from ocrdmonitor.server.settings import (
    OcrdBrowserSettings,
    OcrdControllerSettings,
    OcrdLogViewSettings,
    Settings,
)
from tests.testdoubles import (
    BackgroundProcess,
    BrowserSpy,
    BrowserTestDoubleFactory,
    InMemoryBrowserProcessRepository,
)

JOB_DIR = Path(__file__).parent / "ocrd.jobs"
WORKSPACE_DIR = Path("tests") / "workspaces"


def create_settings() -> Settings:
    return Settings(
        ocrd_browser=OcrdBrowserSettings(
            workspace_dir=WORKSPACE_DIR,
            port_range=(9000, 9100),
            db_connection_string="",
        ),
        ocrd_controller=OcrdControllerSettings(
            job_dir=JOB_DIR,
            host="",
            user="",
        ),
        ocrd_logview=OcrdLogViewSettings(port=8022),
    )


@asynccontextmanager
async def patch_factory(
    factory: BrowserTestDoubleFactory,
) -> AsyncIterator[BrowserTestDoubleFactory]:
    async with factory:
        with patch.object(OcrdBrowserSettings, "factory", lambda _: factory):
            yield factory


@asynccontextmanager
async def mongodb_repository(
    restoring_factory: BrowserRestoringFactory,
) -> AsyncIterator[dbmodel.MongoBrowserProcessRepository]:
    with MongoDbContainer() as container:
        await dbmodel.init(container.get_connection_url())
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
        return BrowserSpy(owner, workspace, address, process_id)

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
    repository_constructor: Callable[
        [BrowserRestoringFactory],
        AsyncContextManager[BrowserProcessRepository],
    ] = request.param
    async with repository_constructor(spy_restoring_factory()) as repository:
        async with patch_repository(repository):
            yield repository


@pytest_asyncio.fixture
async def app() -> TestClient:
    return TestClient(await create_app(create_settings()))


def _launch_app() -> None:
    app = create_app(create_settings())
    uvicorn.run(app, port=3000)


@pytest.fixture
def launch_monitor() -> Iterator[None]:
    with BackgroundProcess(_launch_app):
        yield
