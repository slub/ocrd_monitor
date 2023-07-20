from beanie.odm.queries.find import FindMany
from typing import Any, Collection, Mapping
import pymongo
from beanie import Document

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.repositories import BrowserRestoringFactory


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
        result = await BrowserProcess.find_one(
            BrowserProcess.owner == browser.owner(),
            BrowserProcess.workspace == browser.workspace(),
            BrowserProcess.address == browser.address(),
            BrowserProcess.process_id == browser.process_id(),
        )

        if not result:
            return

        await result.delete()

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

        if results is None:
            results = BrowserProcess.find_all()

        return [
            self._restoring_factory(
                browser.owner,
                browser.workspace,
                browser.address,
                browser.process_id,
            )
            for browser in await results.to_list()
        ]

    async def first(self, owner: str, workspace: str) -> OcrdBrowser | None:
        result = await BrowserProcess.find_one(
            BrowserProcess.owner == owner,
            BrowserProcess.workspace == workspace,
        )

        if result is None:
            return None

        return self._restoring_factory(
            result.owner,
            result.workspace,
            result.address,
            result.process_id,
        )

    async def count(self) -> int:
        return await BrowserProcess.count()

    async def clean(self) -> None:
        await BrowserProcess.delete_all()