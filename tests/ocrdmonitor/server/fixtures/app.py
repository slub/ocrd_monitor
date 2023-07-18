from typing import AsyncIterator

import pytest_asyncio
from fastapi.testclient import TestClient

from tests.ocrdmonitor.server.fixtures.environment import Fixture


@pytest_asyncio.fixture
async def app() -> AsyncIterator[TestClient]:
    async with Fixture() as env:
        yield env.app
