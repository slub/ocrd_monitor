from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from tests import markers
from tests.testdoubles import BrowserFake, BrowserSpy

from .environment import Fixture, RepositoryInitializer
from .repository import inmemory_repository, mongodb_repository


@pytest.fixture(
    params=[
        inmemory_repository,
        pytest.param(
            mongodb_repository,
            marks=(pytest.mark.integration, markers.skip_if_no_docker),
        ),
    ]
)
def repository_fixture(request: pytest.FixtureRequest) -> Fixture:
    repository: RepositoryInitializer = request.param
    return Fixture().with_repository_type(repository)


@pytest.fixture(
    params=[BrowserSpy, pytest.param(BrowserFake, marks=pytest.mark.integration)]
)
def browser_fixture(
    repository_fixture: Fixture, request: pytest.FixtureRequest
) -> Fixture:
    return repository_fixture.with_browser_type(request.param)


@pytest_asyncio.fixture
async def app() -> AsyncIterator[TestClient]:
    async with Fixture() as env:
        yield env.app
