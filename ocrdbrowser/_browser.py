from __future__ import annotations
import asyncio

from os import path
from typing import AsyncContextManager, Protocol


class OcrdBrowser(Protocol):
    def process_id(self) -> str:
        ...

    def address(self) -> str:
        ...

    def owner(self) -> str:
        ...

    def workspace(self) -> str:
        ...

    def client(self) -> OcrdBrowserClient:
        ...

    async def stop(self) -> None:
        ...


class ChannelClosed(RuntimeError):
    ...


class Channel(Protocol):
    async def receive_bytes(self) -> bytes:
        ...

    async def send_bytes(self, data: bytes) -> None:
        ...


class OcrdBrowserClient(Protocol):
    async def get(self, resource: str) -> bytes:
        ...

    def open_channel(self) -> AsyncContextManager[Channel]:
        ...


class OcrdBrowserFactory(Protocol):
    async def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        ...
