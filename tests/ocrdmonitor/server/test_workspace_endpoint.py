from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import Response

from tests.ocrdmonitor.server import scraping
from tests.ocrdmonitor.server.fixtures.environment import (
    DevEnvironment,
    Fixture,
)
from tests.ocrdmonitor.server.fixtures.settings import WORKSPACE_DIR
from tests.testdoubles import (
    Browser_Heading,
    BrowserSpy,
    browser_with_disconnecting_channel,
    unreachable_browser,
)


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
async def defaultenv(browser_fixture: Fixture) -> AsyncIterator[DevEnvironment]:
    async with browser_fixture as env:
        yield env


def test__workspaces__shows_the_workspace_names_starting_from_workspace_root(
    app: TestClient,
) -> None:
    result = app.get("/workspaces")

    texts = scraping.parse_texts(result.content, "li > a")
    assert set(texts) == {"a_workspace", "another workspace", "nested/workspace"}


@pytest.mark.asyncio
async def test__browse_workspace__passes_full_workspace_path_to_ocrdbrowser(
    repository_fixture: Fixture,
) -> None:
    workspace = "a_workspace"
    full_workspace = str(WORKSPACE_DIR / workspace)
    browser = BrowserSpy()
    fixture = repository_fixture.with_browser_type(lambda: browser)

    async with fixture as env:
        response = open_workspace(env.app, workspace)

        assert browser.is_running is True
        assert browser.workspace() == full_workspace
        assert response.status_code == 200


def test__browse_workspace__assigns_and_tracks_session_id(
    app: TestClient,
) -> None:
    response = open_workspace(app, "a_workspace")
    first_session_id = response.cookies.get("session_id")

    response = app.get("/workspaces/browse/a_workspace")
    second_session_id = response.cookies.get("session_id")

    assert first_session_id is not None
    assert first_session_id == second_session_id


@pytest.mark.asyncio
async def test__opened_workspace__when_socket_disconnects__shuts_down_browser(
    browser_fixture: Fixture,
) -> None:
    session_id = "the-owner"
    disconnecting_browser = browser_with_disconnecting_channel(
        session_id, str(WORKSPACE_DIR / "a_workspace")
    )

    fixture = browser_fixture.with_running_browsers(
        disconnecting_browser
    ).with_session_id(session_id)

    async with fixture as env:
        _ = interact_with_workspace(env.app, "a_workspace")

    assert disconnecting_browser.is_running is False


@pytest.mark.asyncio
async def test__disconnected_workspace__when_opening_again__viewing_proxies_requests_to_browser(
    browser_fixture: Fixture,
) -> None:
    session_id = "the-owner"
    workspace = "a_workspace"
    full_workspace = str(WORKSPACE_DIR / workspace)
    fixture = browser_fixture.with_running_browsers(
        browser_with_disconnecting_channel(session_id, full_workspace)
    ).with_session_id(session_id)

    async with fixture as env:
        _ = interact_with_workspace(env.app, workspace)

        actual = interact_with_workspace(env.app, workspace)

    assert_is_browser_response(actual)


@pytest.mark.asyncio
async def test__when_requesting_resource__returns_resource_from_workspace(
    browser_fixture: Fixture,
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

    fixture = browser_fixture.with_running_browsers(browser).with_session_id(session_id)

    async with fixture as env:
        open_workspace(env.app, workspace)

        actual = view_workspace(env.app, resource_in_workspace)

        assert actual.content == resource.encode()


def test__browsed_workspace_is_ready__when_pinging__returns_ok(
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = interact_with_workspace(app, workspace)

    result = app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 200


@pytest.mark.asyncio
async def test__browsed_workspace_not_ready__when_pinging__returns_bad_gateway(
    repository_fixture: Fixture,
) -> None:
    workspace = "a_workspace"
    fixture = repository_fixture.with_browser_type(unreachable_browser)

    async with fixture as env:
        open_workspace(env.app, workspace)

        result = env.app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 502


@pytest.mark.asyncio
async def test__browsing_workspace__stores_browser_in_repository(
    defaultenv: DevEnvironment,
) -> None:
    _ = interact_with_workspace(defaultenv.app, "a_workspace")

    found_browsers = list(
        await defaultenv._repositories.browser_processes.find(
            workspace=str(WORKSPACE_DIR / "a_workspace")
        )
    )

    assert len(found_browsers) == 1


@pytest.mark.asyncio
async def test__error_connecting_to_workspace__removes_browser_from_repository(
    repository_fixture: Fixture,
) -> None:
    fixture = repository_fixture.with_browser_type(unreachable_browser)
    async with fixture as env:
        open_workspace(env.app, "a_workspace")
        _ = view_workspace(env.app, "a_workspace")

        browsers = await env._repositories.browser_processes.find(
            workspace=str(WORKSPACE_DIR / "a_workspace")
        )

    assert len(list(browsers)) == 0


@pytest.mark.asyncio
async def test__when_socket_to_workspace_disconnects__removes_browser_from_repository(
    repository_fixture: Fixture,
) -> None:
    # NOTE: it seems something is weird with the event loop in this test
    # Searching for browsers inside the with block happens BEFORE the browser is deleted
    # I'm not sure if this is a bug in the FastAPI TestClient or if we're doing something wrong here
    # We apply a little hack and sleep for .1 seconds, handing control back to the event loop

    fixture = repository_fixture.with_browser_type(browser_with_disconnecting_channel)

    async with fixture as env:
        _ = interact_with_workspace(env.app, "a_workspace")
        await asyncio.sleep(0.1)

        browsers = await env._repositories.browser_processes.find(
            workspace=str(WORKSPACE_DIR / "a_workspace")
        )

        assert len(list(browsers)) == 0


@pytest.mark.asyncio
async def test__browser_stored_in_repo__when_browsing_workspace_redirects_to_restored_browser(
    browser_fixture: Fixture,
) -> None:
    session_id = "the-owner"
    workspace = "a_workspace"
    full_workspace = str(WORKSPACE_DIR / workspace)
    browser = BrowserSpy(session_id, full_workspace)
    browser.configure_client(response=b"RESTORED BROWSER")

    fixture = browser_fixture.with_running_browsers(browser).with_session_id(session_id)

    async with fixture as env:
        response = interact_with_workspace(env.app, "a_workspace")

    assert response.content == b"RESTORED BROWSER"
