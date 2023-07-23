import asyncio
import urllib
from typing import Protocol

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from ._browserprocessrepository import BrowserProcess
from ._ocrdjobrepository import MongoOcrdJob


def rebuild_connection_string(connection_str: str) -> str:
    connection_str = connection_str.removeprefix("mongodb://")
    credentials, host = connection_str.split("@")
    user, password = credentials.split(":")
    password = urllib.parse.quote(password)
    return f"mongodb://{user}:{password}@{host}"


class InitDatabase(Protocol):
    async def __call__(
        self, connection_str: str, force_initialize: bool = False
    ) -> None:
        ...


def __beanie_initializer() -> InitDatabase:
    """
    We use this as a workaround to prevent beanie from being initialized
    multiple times when requesting the repository from OcrdBrowserSettings
    unless stated explicitly (e.g. for testing purposes)
    """
    __initialized = False

    async def init(connection_str: str, force_initialize: bool = False) -> None:
        nonlocal __initialized
        if __initialized and not force_initialize:
            return

        __initialized = True
        connection_str = rebuild_connection_string(connection_str)
        client: AsyncIOMotorClient = AsyncIOMotorClient(connection_str)
        client.get_io_loop = asyncio.get_event_loop
        await init_beanie(
            database=client.ocrd,
            document_models=[BrowserProcess, MongoOcrdJob],  # type: ignore
        )

    return init


init = __beanie_initializer()
