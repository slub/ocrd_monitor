from __future__ import annotations

from typing import Iterator
from httpx import Response

import pytest
from fastapi.testclient import TestClient

from ocrdbrowser import ChannelClosed, OcrdBrowser, OcrdBrowserFactory
from ocrdmonitor.server.settings import OcrdBrowserSettings
from tests.fakes import BrowserFakeFactory, BrowserFake, BROWSERFAKE_HEADER
from tests.ocrdbrowser.browserdoubles import (
    BrowserSpy,
    BrowserTestDoubleFactory,
    ChannelDummy,
)
from tests.ocrdmonitor.server import scraping
from tests.ocrdmonitor.server.fixtures import WORKSPACE_DIR


class DisconnectingChannel:
    async def send_bytes(self, data: bytes) -> None:
        raise ChannelClosed()

    async def receive_bytes(self) -> bytes:
        raise ChannelClosed()


@pytest.fixture
def browser_spy(monkeypatch: pytest.MonkeyPatch) -> BrowserSpy:
    browser_spy = BrowserSpy()

    def factory(_: OcrdBrowserSettings) -> OcrdBrowserFactory:
        def _factory(owner: str, workspace_path: str) -> OcrdBrowser:
            browser_spy.owner_name = owner
            browser_spy.workspace_path = workspace_path
            return browser_spy

        return _factory

    monkeypatch.setattr(OcrdBrowserSettings, "factory", factory)
    return browser_spy


@pytest.fixture
def use_browser_fakes(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    fake_factory = BrowserFakeFactory()

    def factory(_: OcrdBrowserSettings) -> OcrdBrowserFactory:
        return fake_factory

    monkeypatch.setattr(OcrdBrowserSettings, "factory", factory)
    with fake_factory:
        yield


@pytest.fixture
def factory__disconnecting_spy__then_browser_fake(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    spy = BrowserSpy(channel=DisconnectingChannel())
    fake = BrowserFake()
    factory = BrowserTestDoubleFactory(spy, fake)
    monkeypatch.setattr(OcrdBrowserSettings, "factory", lambda _: factory)

    yield

    fake.stop()


def assert_is_fake_browser_response(actual: Response) -> None:
    assert scraping.parse_texts(actual.content, "h1") == [BROWSERFAKE_HEADER]


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
    browser_spy: BrowserSpy,
    app: TestClient,
) -> None:
    response = app.get("/workspaces/browse/a_workspace")

    assert browser_spy.running is True
    assert browser_spy.workspace() == str(WORKSPACE_DIR / "a_workspace")
    assert response.status_code == 200


@pytest.mark.usefixtures("browser_spy")
def test__browse_workspace__assigns_and_tracks_session_id(app: TestClient) -> None:
    response = app.get("/workspaces/browse/a_workspace")
    first_session_id = response.cookies.get("session_id")

    response = app.get("/workspaces/browse/a_workspace")
    second_session_id = response.cookies.get("session_id")

    assert first_session_id is not None
    assert first_session_id == second_session_id


def test__opened_workspace__when_socket_disconnects_on_broadway_side_while_viewing__shuts_down_browser(
    browser_spy: BrowserSpy,
    app: TestClient,
) -> None:
    browser_spy.channel = DisconnectingChannel()
    _ = view_workspace(app, "a_workspace")

    assert browser_spy.running is False


def test__disconnected_workspace__when_opening_again__starts_new_browser(
    browser_spy: BrowserSpy,
    app: TestClient,
) -> None:
    browser_spy.channel = DisconnectingChannel()

    workspace = "a_workspace"
    _ = view_workspace(app, workspace)

    browser_spy.channel = ChannelDummy()
    _ = view_workspace(app, workspace)

    assert browser_spy.running is True


@pytest.mark.usefixtures("factory__disconnecting_spy__then_browser_fake")
def test__disconnected_workspace__when_opening_again__viewing_proxies_requests_to_browser(
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = view_workspace(app, workspace)

    actual = view_workspace(app, workspace)

    assert_is_fake_browser_response(actual)


@pytest.mark.usefixtures("use_browser_fakes")
def test__browsed_workspace_is_ready__when_pinging__returns_ok(
    app: TestClient,
) -> None:
    workspace = "a_workspace"
    _ = view_workspace(app, workspace)

    result = app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 200


@pytest.mark.usefixtures("browser_spy")
def test__browsed_workspace_not_ready__when_pinging__returns_bad_gateway(
    app: TestClient,
) -> None:
    """
    We're using a browser spy here, because it's not a real server and therefore will not be reachable
    """
    workspace = "a_workspace"
    _ = view_workspace(app, workspace)

    result = app.get(f"/workspaces/ping/{workspace}")

    assert result.status_code == 502
