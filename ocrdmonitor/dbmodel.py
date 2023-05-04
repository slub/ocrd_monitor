import asyncio
from typing import Any, Collection, Mapping

import pymongo
from beanie import Document, init_beanie
from beanie.odm.queries.find import FindMany
from motor.motor_asyncio import AsyncIOMotorClient

from ocrdmonitor.browserprocess import BrowserProcess as BrowserProcessProtocol


class BrowserProcess(Document):
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
    async def insert(self, browser: BrowserProcessProtocol) -> None:
        await BrowserProcess(
            owner=browser.owner,
            process_id=browser.process_id,
            workspace=browser.workspace,
        ).insert()

    async def delete(self, browser: BrowserProcessProtocol) -> None:
        await BrowserProcess(
            owner=browser.owner,
            process_id=browser.process_id,
            workspace=browser.workspace,
        ).delete()

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
        process_id: str | None = None,
    ) -> Collection[BrowserProcess]:
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

        if process_id is not None:
            results = find(results, BrowserProcess.process_id == process_id)

        return await results.to_list() if results is not None else []


async def init(connection_str: str) -> None:
    client: AsyncIOMotorClient = AsyncIOMotorClient(connection_str)
    client.get_io_loop = asyncio.get_event_loop
    await init_beanie(
        database=client.browsers,
        document_models=[BrowserProcess],  # type: ignore
    )
