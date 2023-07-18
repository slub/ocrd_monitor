from __future__ import annotations

from typing import AsyncIterator, cast

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import Response

from tests.ocrdmonitor.server import scraping
from tests.ocrdmonitor.server.decorators import use_custom_repository
from tests.ocrdmonitor.server.fixtures.app import WORKSPACE_DIR
from tests.ocrdmonitor.server.fixtures.environment import Environment, Fixture
from tests.ocrdmonitor.server.fixtures.factory import patch_factory
from tests.ocrdmonitor.server.fixtures.repository import (
    RepositoryInitializer,
)
from tests.testdoubles import (
    Browser_Heading,
    BrowserFake,
    BrowserSpy,
    BrowserTestDouble,
    BrowserTestDoubleFactory,
    IteratingBrowserTestDoubleFactory,
    browser_with_disconnecting_channel,
    unreachable_browser,
)


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
    disconnecting_browser = browser_with_disconnecting_channel()
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


def open_workspace(app: TestClient, workspace: str) -> Response:
    _ = app.get(f"/workspaces/open/{workspace}")
    return app.get(f"/workspaces/browse/{workspace}")


def view_workspace(app: TestClient, workspace: str) -> Response:
    return app.get(f"/workspaces/view/{workspace}")


@pytest_asyncio.fixture
async def defaultenv() -> AsyncIterator[Environment]:
    async with Fixture() as env:
        yield env


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
    response = open_workspace(app, "a_workspace")

    assert browser.is_running is True
    assert browser.workspace() == str(WORKSPACE_DIR / "a_workspace")
    assert response.status_code == 200


def test__browse_workspace__assigns_and_tracks_session_id(
    defaultenv: Environment,
) -> None:
    app = defaultenv.app
    response = open_workspace(app, "a_workspace")
    first_session_id = response.cookies.get("session_id")

    response = app.get("/workspaces/browse/a_workspace")
    second_session_id = response.cookies.get("session_id")

    assert first_session_id is not None
    assert first_session_id == second_session_id


@pytest.mark.asyncio
@use_custom_repository
async def test__opened_workspace__when_socket_disconnects__shuts_down_browser(
    repository: RepositoryInitializer,
) -> None:
    session_id = "the-owner"
    disconnecting_browser = browser_with_disconnecting_channel(
        session_id, str(WORKSPACE_DIR / "a_workspace")
    )
    fixture = (
        Fixture()
        .with_repository_type(repository)
        .with_running_browsers(disconnecting_browser)
        .with_session_id(session_id)
    )

    async with fixture as env:
        _ = interact_with_workspace(env.app, "a_workspace")

    assert disconnecting_browser.is_running is False


@pytest.mark.usefixtures("disconnecting_browser")
def test__disconnected_workspace__when_opening_again__viewing_proxies_requests_to_browser(
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = interact_with_workspace(app, workspace)

    actual = interact_with_workspace(app, workspace)

    assert_is_browser_response(actual)


@pytest.mark.asyncio
@use_custom_repository
async def test__when_requesting_resource__returns_resource_from_workspace(
    repository: RepositoryInitializer,
) -> None:
    session_id = "the-owner"

    workspace = "a_workspace"
    resource = "/some_resource"
    resource_in_workspace = workspace + "/some_resource"
    full_workspace = str(WORKSPACE_DIR / workspace)

    def echo_bytes(path: str) -> bytes:
        return path.encode()

    browser = BrowserSpy(session_id, full_workspace)
    browser.configure_client(response_factory=echo_bytes)

    fixture = (
        Fixture()
        .with_repository_type(repository)
        .with_running_browsers(browser)
        .with_session_id(session_id)
    )

    async with fixture as env:
        open_workspace(env.app, workspace)

        actual = view_workspace(env.app, resource_in_workspace)

        assert actual.content == resource.encode()


def test__browsed_workspace_is_ready__when_pinging__returns_ok(
    defaultenv: Environment,
) -> None:
    app = defaultenv.app
    workspace = "a_workspace"
    _ = interact_with_workspace(app, workspace)

    result = app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 200


@use_custom_repository
async def test__browsed_workspace_not_ready__when_pinging__returns_bad_gateway(
    repository: RepositoryInitializer,
) -> None:
    workspace = "a_workspace"
    fixture = (
        Fixture()
        .with_browser_type(unreachable_browser)
        .with_repository_type(repository)
    )

    async with fixture as env:
        open_workspace(env.app, workspace)

        result = env.app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 502


@use_custom_repository
async def test__browsing_workspace__stores_browser_in_repository(
    repository: RepositoryInitializer,
) -> None:
    fixture = Fixture().with_repository_type(repository)

    async with fixture as env:
        _ = interact_with_workspace(env.app, "a_workspace")

        found_browsers = list(
            await env.repository.find(workspace=str(WORKSPACE_DIR / "a_workspace"))
        )

    assert len(found_browsers) == 1


@use_custom_repository
async def test__error_connecting_to_workspace__removes_browser_from_repository(
    repository: RepositoryInitializer,
) -> None:
    fixture = (
        Fixture()
        .with_browser_type(unreachable_browser)
        .with_repository_type(repository)
    )

    async with fixture as env:
        open_workspace(env.app, "a_workspace")
        _ = view_workspace(env.app, "a_workspace")

        found_browsers = list(
            await env.repository.find(workspace=str(WORKSPACE_DIR / "a_workspace"))
        )

        assert len(found_browsers) == 0


@use_custom_repository
async def test__when_socket_to_workspace_disconnects__removes_browser_from_repository(
    repository: RepositoryInitializer,
) -> None:
    # NOTE: it seems something is weird with the event loop in this test.
    # Searching for browsers inside the with block happens BEFORE the browser is deleted.
    # Therefore we run the lookup after the contextmanager has been closed

    fixture = (
        Fixture()
        .with_repository_type(repository)
        .with_browser_type(browser_with_disconnecting_channel)
    )

    async with fixture as env:
        _ = interact_with_workspace(env.app, "a_workspace")

    found_browsers = list(
        await env.repository.find(workspace=str(WORKSPACE_DIR / "a_workspace"))
    )

    assert len(found_browsers) == 0


@use_custom_repository
async def test__browser_stored_in_repo__when_browsing_workspace_redirects_to_restored_browser(
    repository: RepositoryInitializer,
) -> None:
    session_id = "the-owner"
    workspace = "a_workspace"
    full_workspace = str(WORKSPACE_DIR / workspace)
    browser = BrowserSpy(session_id, full_workspace)
    browser.configure_client(response=b"RESTORED BROWSER")

    fixture = (
        Fixture()
        .with_repository_type(repository)
        .with_running_browsers(browser)
        .with_session_id(session_id)
    )

    async with fixture as env:
        response = interact_with_workspace(env.app, "a_workspace")

    assert response.content == b"RESTORED BROWSER"
