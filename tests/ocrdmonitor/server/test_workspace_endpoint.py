from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import (
    AsyncContextManager,
    AsyncIterator,
    Callable,
    ContextManager,
    Iterator,
    cast,
)

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import Response
from testcontainers.mongodb import MongoDbContainer

from ocrdbrowser import ChannelClosed
from ocrdmonitor import dbmodel
from ocrdmonitor.browserprocess import BrowserProcessRepository
from ocrdmonitor.server.settings import OcrdBrowserSettings
from tests.ocrdmonitor.server import scraping
from tests.ocrdmonitor.server.fixtures import (
    WORKSPACE_DIR,
    patch_factory,
)
from tests.testdoubles import (
    Browser_Heading,
    BrowserFake,
    BrowserSpy,
    BrowserTestDouble,
    BrowserTestDoubleFactory,
    InMemoryBrowserProcessRepository,
    IteratingBrowserTestDoubleFactory,
    SingletonBrowserTestDoubleFactory,
)


class DisconnectingChannel:
    async def send_bytes(self, data: bytes) -> None:
        raise ChannelClosed()

    async def receive_bytes(self) -> bytes:
        raise ChannelClosed()


@pytest_asyncio.fixture(
    params=(BrowserSpy, pytest.param(BrowserFake, marks=pytest.mark.integration))
)
async def iterating_factory(
    request: pytest.FixtureRequest,
) -> AsyncIterator[BrowserTestDoubleFactory]:
    async with patch_factory(
        IteratingBrowserTestDoubleFactory(default_browser=request.param)
    ) as factory:
        yield factory


@pytest_asyncio.fixture
async def singleton_browser_spy() -> AsyncIterator[BrowserSpy]:
    browser_spy = BrowserSpy()
    async with patch_factory(SingletonBrowserTestDoubleFactory(browser_spy)):
        yield browser_spy


@pytest.fixture(
    params=(BrowserSpy, pytest.param(BrowserFake, marks=pytest.mark.integration))
)
def browser(
    iterating_factory: IteratingBrowserTestDoubleFactory,
    request: pytest.FixtureRequest,
) -> BrowserTestDouble:
    browser_type = request.param
    browser = cast(BrowserTestDouble, browser_type())
    iterating_factory.add(browser)

    return browser


@pytest.fixture
def disconnecting_browser(
    iterating_factory: IteratingBrowserTestDoubleFactory,
) -> BrowserSpy:
    disconnecting_browser = BrowserSpy()
    disconnecting_browser.configure_client(channel=DisconnectingChannel())
    iterating_factory.add(disconnecting_browser)

    return disconnecting_browser


def assert_is_browser_response(actual: Response) -> None:
    assert scraping.parse_texts(actual.content, "h1") == [Browser_Heading]


def view_workspace(app: TestClient, workspace: str) -> Response:
    _ = app.get(f"/workspaces/browse/{workspace}")
    response = app.get(f"/workspaces/view/{workspace}")
    with app.websocket_connect(f"/workspaces/view/{workspace}/socket"):
        pass

    return response


def test__workspaces__shows_the_workspace_names_starting_from_workspace_root(
    app: TestClient,
) -> None:
    result = app.get("/workspaces")

    texts = scraping.parse_texts(result.content, "li > a")
    assert set(texts) == {"a_workspace", "another workspace", "nested/workspace"}


def test__browse_workspace__passes_full_workspace_path_to_ocrdbrowser(
    browser: BrowserTestDouble,
    app: TestClient,
) -> None:
    response = app.get("/workspaces/browse/a_workspace")

    assert browser.is_running is True
    assert browser.workspace() == str(WORKSPACE_DIR / "a_workspace")
    assert response.status_code == 200


@pytest.mark.usefixtures("iterating_factory")
def test__browse_workspace__assigns_and_tracks_session_id(app: TestClient) -> None:
    response = app.get("/workspaces/browse/a_workspace")
    first_session_id = response.cookies.get("session_id")

    response = app.get("/workspaces/browse/a_workspace")
    second_session_id = response.cookies.get("session_id")

    assert first_session_id is not None
    assert first_session_id == second_session_id


def test__opened_workspace__when_socket_disconnects_on_broadway_side__shuts_down_browser(
    disconnecting_browser: BrowserSpy,
    app: TestClient,
) -> None:
    _ = view_workspace(app, "a_workspace")

    assert disconnecting_browser.is_running is False


def test__disconnected_workspace__when_opening_again__starts_new_browser(
    disconnecting_browser: BrowserTestDouble,
    browser: BrowserTestDouble,
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = view_workspace(app, workspace)

    _ = view_workspace(app, workspace)

    assert disconnecting_browser.is_running is False
    assert browser.is_running is True


@pytest.mark.usefixtures("disconnecting_browser")
def test__disconnected_workspace__when_opening_again__viewing_proxies_requests_to_browser(
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = view_workspace(app, workspace)

    actual = view_workspace(app, workspace)

    assert_is_browser_response(actual)


@pytest.mark.usefixtures("iterating_factory")
def test__browsed_workspace_is_ready__when_pinging__returns_ok(
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = view_workspace(app, workspace)

    result = app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 200


def test__browsed_workspace_not_ready__when_pinging__returns_bad_gateway(
    singleton_browser_spy: BrowserSpy,
    app: TestClient,
) -> None:
    singleton_browser_spy.configure_client(response=ConnectionError)
    workspace = "a_workspace"
    _ = view_workspace(app, workspace)

    result = app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 502


@pytest.mark.asyncio
@pytest.mark.usefixtures("iterating_factory")
async def test__browsing_workspace__stores_browser_in_repository(
    repository: BrowserProcessRepository, app: TestClient
) -> None:
    _ = view_workspace(app, "a_workspace")

    found_browsers = await repository.find(workspace=str(WORKSPACE_DIR / "a_workspace"))

    assert len(found_browsers) == 1
