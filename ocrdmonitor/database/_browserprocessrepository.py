from datetime import datetime
from typing import Any, Callable, Collection, Mapping

import pymongo
from beanie import Document
from beanie.odm.queries.find import FindMany

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.protocols import BrowserRestoringFactory


class BrowserProcess(Document):
    address: str
    owner: str
    process_id: str
    workspace: str
    last_access_time: datetime

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
    def __init__(
        self, restoring_factory: BrowserRestoringFactory, clock: Callable[[], datetime]
    ) -> None:
        self._restoring_factory = restoring_factory
        self._clock = clock

    async def insert(self, browser: OcrdBrowser) -> None:
        await BrowserProcess(  # type: ignore
            address=browser.address(),
            owner=browser.owner(),
            process_id=browser.process_id(),
            workspace=browser.workspace(),
            last_access_time=self._clock(),
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

        result.last_access_time = self._clock()
        await result.save()
        return self._restoring_factory(
            result.owner,
            result.workspace,
            result.address,
            result.process_id,
        )

    async def browsers_accessed_before(self, time: datetime) -> list[OcrdBrowser]:
        return [
            self._restoring_factory(
                **p.model_dump(exclude={"id", "revision_id", "last_access_time"})
            )
            for p in await BrowserProcess.find(
                BrowserProcess.last_access_time < time
            ).to_list()
        ]

    async def count(self) -> int:
        return await BrowserProcess.count()

    async def clean(self) -> None:
        await BrowserProcess.delete_all()
