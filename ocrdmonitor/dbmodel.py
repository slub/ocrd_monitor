import asyncio
from typing import Any, Collection, Mapping

import pymongo
import urllib
from beanie import Document, init_beanie
from beanie.odm.queries.find import FindMany
from motor.motor_asyncio import AsyncIOMotorClient

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.browserprocess import BrowserRestoringFactory


class BrowserProcess(Document):
    address: str
    owner: str
    process_id: str
    workspace: str

    class Settings:
        indexes = [
            pymongo.IndexModel(
                [
                    ("owner", pymongo.ASCENDING),
                    ("workspace", pymongo.ASCENDING),
                ]
            )
        ]


class MongoBrowserProcessRepository:
    def __init__(self, restoring_factory: BrowserRestoringFactory) -> None:
        self._restoring_factory = restoring_factory

    async def insert(self, browser: OcrdBrowser) -> None:
        await BrowserProcess(  # type: ignore
            address=browser.address(),
            owner=browser.owner(),
            process_id=browser.process_id(),
            workspace=browser.workspace(),
        ).insert()

    async def delete(self, browser: OcrdBrowser) -> None:
        await BrowserProcess.find_one(
            BrowserProcess.owner == browser.owner(),
            BrowserProcess.workspace == browser.workspace(),
            BrowserProcess.address == browser.address(),
            BrowserProcess.process_id == browser.process_id(),
        ).delete()

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
    ) -> Collection[OcrdBrowser]:
        results: FindMany[BrowserProcess] | None = None

        def find(
            results: FindMany[BrowserProcess] | None,
            *predicates: Mapping[str, Any] | bool,
        ) -> FindMany[BrowserProcess]:
            if results is None:
                return BrowserProcess.find(*predicates)

            return results.find(*predicates)

        if owner is not None:
            results = find(results, BrowserProcess.owner == owner)

        if workspace is not None:
            results = find(results, BrowserProcess.workspace == workspace)

        return (
            [
                self._restoring_factory(
                    browser.owner,
                    browser.workspace,
                    browser.address,
                    browser.process_id,
                )
                for browser in await results.to_list()
            ]
            if results
            else []
        )

    async def first(self, owner: str, workspace: str) -> OcrdBrowser | None:
        result = await BrowserProcess.find_one(
            BrowserProcess.owner == owner,
            BrowserProcess.workspace == workspace,
        )

        return self._restoring_factory(
            result.owner,
            result.workspace,
            result.address,
            result.process_id,
        )

    async def clean(self) -> None:
        await BrowserProcess.delete_all()


async def init(connection_str: str) -> None:
    connection_str = connection_str.removeprefix("mongodb://")
    credentials, host = connection_str.split("@")
    user, password = credentials.split(":")
    password = urllib.parse.quote(password)
    connection_str = f"mongodb://{user}:{password}@{host}"
    client: AsyncIOMotorClient = AsyncIOMotorClient(connection_str)
    client.get_io_loop = asyncio.get_event_loop
    await init_beanie(
        database=client.browsers,
        document_models=[BrowserProcess],  # type: ignore
    )
