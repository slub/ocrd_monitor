from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Iterator
from unittest.mock import patch

import pytest
import uvicorn
from fastapi.testclient import TestClient

from ocrdmonitor.server.app import create_app
from ocrdmonitor.server.settings import (
    OcrdBrowserSettings,
    OcrdControllerSettings,
    OcrdLogViewSettings,
    Settings,
)
from tests.testdoubles import BackgroundProcess, BrowserTestDoubleFactory

JOB_DIR = Path(__file__).parent / "ocrd.jobs"
WORKSPACE_DIR = Path("tests") / "workspaces"


def create_settings() -> Settings:
    return Settings(
        ocrd_browser=OcrdBrowserSettings(
            workspace_dir=WORKSPACE_DIR,
            port_range=(9000, 9100),
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


@pytest.fixture
def app() -> TestClient:
    return TestClient(create_app(create_settings()))


def _launch_app() -> None:
    app = create_app(create_settings())
    uvicorn.run(app, port=3000)


@pytest.fixture
def launch_monitor() -> Iterator[None]:
    with BackgroundProcess(_launch_app):
        yield
