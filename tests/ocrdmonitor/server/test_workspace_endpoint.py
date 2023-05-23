from __future__ import annotations

from typing import AsyncIterator, cast

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import Response

from ocrdbrowser import ChannelClosed
from ocrdmonitor.browserprocess import BrowserProcessRepository
from ocrdmonitor.server.app import create_app
from tests.ocrdmonitor.server import scraping
from tests.ocrdmonitor.server.decorators import use_custom_repository
from tests.ocrdmonitor.server.fixtures.app import WORKSPACE_DIR, create_settings
from tests.ocrdmonitor.server.fixtures.factory import patch_factory
from tests.ocrdmonitor.server.fixtures.repository import (
    RepositoryInitializer,
    patch_repository,
)
from tests.testdoubles import (
    Browser_Heading,
    BrowserFake,
    BrowserSpy,
    BrowserTestDouble,
    BrowserTestDoubleFactory,
    IteratingBrowserTestDoubleFactory,
    SingletonBrowserTestDoubleFactory,
)
from tests.testdoubles._browserfactory import SingletonRestoringBrowserFactory


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


def interact_with_workspace(app: TestClient, workspace: str) -> Response:
    open_workspace(app, workspace)
    response = view_workspace(app, workspace)
    with app.websocket_connect(f"/workspaces/view/{workspace}/socket"):
        pass

    return response


def open_workspace(app: TestClient, workspace: str) -> None:
    _ = app.get(f"/workspaces/browse/{workspace}")


def view_workspace(app: TestClient, workspace: str) -> Response:
    return app.get(f"/workspaces/view/{workspace}")


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


@pytest.mark.usefixtures("iterating_factory")
@use_custom_repository
async def test__opened_workspace__when_socket_disconnects_on_broadway_side__shuts_down_browser(
    repository: RepositoryInitializer,
) -> None:
    factory = SingletonRestoringBrowserFactory()
    disconnecting_browser = factory.browser
    disconnecting_browser.configure_client(channel=DisconnectingChannel())

    async with repository(factory) as repo:
        async with patch_repository(repo):
            app = TestClient(await create_app(create_settings()))
            await repo.insert(disconnecting_browser)

            _ = interact_with_workspace(app, "a_workspace")

    assert disconnecting_browser.is_running is False


@pytest.mark.usefixtures("disconnecting_browser")
def test__disconnected_workspace__when_opening_again__viewing_proxies_requests_to_browser(
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = interact_with_workspace(app, workspace)

    actual = interact_with_workspace(app, workspace)

    assert_is_browser_response(actual)


@pytest.mark.usefixtures("iterating_factory")
def test__browsed_workspace_is_ready__when_pinging__returns_ok(
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = interact_with_workspace(app, workspace)

    result = app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 200


@pytest.mark.usefixtures("iterating_factory")
@use_custom_repository
async def test__browsed_workspace_not_ready__when_pinging__returns_bad_gateway(
    singleton_restoring_factory: SingletonRestoringBrowserFactory,
    repository: RepositoryInitializer,
) -> None:
    async with repository(singleton_restoring_factory) as repo:
        async with patch_repository(repo):
            app = TestClient(await create_app(create_settings()))

            browser = singleton_restoring_factory.browser
            browser.configure_client(response=ConnectionError)

            workspace = "a_workspace"
            open_workspace(app, workspace)

            result = app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 502


@pytest.mark.asyncio
@pytest.mark.usefixtures("iterating_factory")
async def test__browsing_workspace__stores_browser_in_repository(
    auto_repository: BrowserProcessRepository, app: TestClient
) -> None:
    _ = interact_with_workspace(app, "a_workspace")

    found_browsers = list(
        await auto_repository.find(workspace=str(WORKSPACE_DIR / "a_workspace"))
    )

    assert len(found_browsers) == 1


@pytest.mark.usefixtures("iterating_factory")
@use_custom_repository
async def test__error_connecting_to_workspace__removes_browser_from_repository(
    singleton_restoring_factory: SingletonRestoringBrowserFactory,
    repository: RepositoryInitializer,
) -> None:
    browser = singleton_restoring_factory.browser
    browser.configure_client(response=ConnectionError)

    async with repository(singleton_restoring_factory) as repo:
        async with patch_repository(repo):
            app = TestClient(await create_app(create_settings()))
            app.cookies.set("session_id", browser.owner())

            open_workspace(app, "a_workspace")
            _ = view_workspace(app, "a_workspace")

            found_browsers = list(
                await repo.find(workspace=str(WORKSPACE_DIR / "a_workspace"))
            )

            assert len(found_browsers) == 0


@pytest.mark.usefixtures("iterating_factory")
@use_custom_repository
async def test__when_socket_to_workspace_disconnects__removes_browser_from_repository(
    singleton_restoring_factory: SingletonRestoringBrowserFactory,
    repository: RepositoryInitializer,
) -> None:
    browser = singleton_restoring_factory.browser
    browser.configure_client(channel=DisconnectingChannel())

    async with repository(singleton_restoring_factory) as repo:
        async with patch_repository(repo):
            app = TestClient(await create_app(create_settings()))
            app.cookies.set("session_id", browser.owner())

            _ = interact_with_workspace(app, "a_workspace")

            found_browsers = list(
                await repo.find(workspace=str(WORKSPACE_DIR / "a_workspace"))
            )

            assert len(found_browsers) == 0


@pytest.mark.usefixtures("iterating_factory")
@use_custom_repository
async def test__browser_stored_in_repo__when_browsing_workspace_redirects_to_restored_browser(
    singleton_restoring_factory: SingletonRestoringBrowserFactory,
    repository: RepositoryInitializer,
) -> None:
    async with repository(singleton_restoring_factory) as repo:
        async with patch_repository(repo):
            app = TestClient(await create_app(create_settings()))

            browser = singleton_restoring_factory.browser
            browser.configure_client(response=b"RESTORED BROWSER")
            await repo.insert(browser)

            response = interact_with_workspace(app, "a_workspace")

    assert response.content == b"RESTORED BROWSER"
