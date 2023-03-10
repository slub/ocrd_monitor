from pathlib import Path

import pytest
from ocrdmonitor.server.redirect import BrowserRedirect

from tests.ocrdbrowser.browserdoubles import BrowserSpy


def server_stub(address: str) -> BrowserSpy:
    return BrowserSpy(address=address)


SERVER_ADDRESS = "http://example.com:8080"


def test__redirect_for_empty_url_returns_server_address() -> None:
    workspace = Path("path/to/workspace")
    browser = server_stub("http://example.com:8080")
    sut = BrowserRedirect(workspace, browser)

    assert sut.redirect_url("") == browser.address()


@pytest.mark.parametrize("address", [SERVER_ADDRESS, SERVER_ADDRESS + "/"])
@pytest.mark.parametrize("filename", ["file.js", "/file.js"])
def test__redirect_to_file_in_workspace__returns_server_slash_file(
    address: str,
    filename: str,
) -> None:
    workspace = Path("path/to/workspace")
    browser = server_stub(address)
    sut = BrowserRedirect(workspace, browser)

    assert sut.redirect_url(filename) == url(address, filename)


def test__redirect_from_workspace__returns_server_address() -> None:
    workspace = Path("path/to/workspace")
    browser = server_stub("http://example.com:8080")
    sut = BrowserRedirect(workspace, browser)

    assert sut.redirect_url(str(workspace)) == browser.address()


def test__redirect_with_workspace__is_a_match() -> None:
    workspace = Path("path/to/workspace")
    browser = server_stub("")
    sut = BrowserRedirect(workspace, browser)

    assert sut.matches(str(workspace)) is True


def test__an_empty_path__does_not_match() -> None:
    workspace = Path("path/to/workspace")
    browser = server_stub("")
    sut = BrowserRedirect(workspace, browser)

    assert sut.matches("") is False


def test__a_path_starting_with_workspace__is_a_match() -> None:
    workspace = Path("path/to/workspace")
    browser = server_stub("")
    sut = BrowserRedirect(workspace, browser)

    sub_path = workspace / "sub" / "path" / "file.txt"
    assert sut.matches(str(sub_path)) is True


def url(server_address: str, subpath: str) -> str:
    server_address = server_address.removesuffix("/")
    subpath = subpath.removeprefix("/")
    return server_address + "/" + subpath
