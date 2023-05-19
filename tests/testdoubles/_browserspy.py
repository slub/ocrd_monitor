from __future__ import annotations

from contextlib import asynccontextmanager
from textwrap import dedent
from typing import AsyncGenerator, Type

from ocrdbrowser import Channel, OcrdBrowserClient

Browser_Heading = "OCRD BROWSER"

html_template = f"""
<!DOCTYPE html>
<html lang="en">
<body>
    <h1>{Browser_Heading}</h1>
</body>
</html>
"""


class ChannelDummy:
    async def send_bytes(self, data: bytes) -> None:
        pass

    async def receive_bytes(self) -> bytes:
        return bytes()


class BrowserClientStub:
    def __init__(
        self, response: bytes | Type[Exception] = b"", channel: Channel | None = None
    ) -> None:
        self.channel = channel or ChannelDummy()
        self.response = response or html_template.encode()

    async def get(self, resource: str) -> bytes:
        if not isinstance(self.response, bytes):
            raise self.response

        return self.response

    @asynccontextmanager
    async def open_channel(self) -> AsyncGenerator[Channel, None]:
        yield self.channel


class BrowserSpy:
    def __init__(
        self,
        owner: str = "",
        workspace: str = "",
        address: str = "http://unreachable.example.com",
        process_id: str = "1234",
        running: bool = False,
    ) -> None:
        self._address = address
        self._process_id = process_id
        self.is_running = running
        self.owner_name = owner
        self.workspace_path = workspace
        self._client = BrowserClientStub()

    def configure_client(
        self, response: bytes | Type[Exception] = b"", channel: Channel | None = None
    ) -> None:
        self._client = BrowserClientStub(response, channel)

    def set_owner_and_workspace(self, owner: str, workspace: str) -> None:
        self.owner_name = owner
        self.workspace_path = workspace

    def process_id(self) -> str:
        return self._process_id

    def address(self) -> str:
        return self._address

    def workspace(self) -> str:
        return self.workspace_path

    def owner(self) -> str:
        return self.owner_name

    def client(self) -> OcrdBrowserClient:
        return self._client

    async def start(self) -> None:
        self.is_running = True

    async def stop(self) -> None:
        self.is_running = False

    def __repr__(self) -> str:
        return dedent(
            f"""
        BrowserSpy:
            workspace: {self.workspace()}
            owner: {self.owner()}
            running: {self.is_running}
        """
        )
