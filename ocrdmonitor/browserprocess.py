from typing import Collection, Protocol
from ocrdbrowser import OcrdBrowser


class BrowserRestoringFactory(Protocol):
    def __call__(
        self, owner: str, workspace: str, address: str, process_id: str
    ) -> OcrdBrowser:
        ...


class BrowserProcessRepository(Protocol):
    async def insert(self, browser: OcrdBrowser) -> None:
        ...

    async def delete(self, browser: OcrdBrowser) -> None:
        ...

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
    ) -> Collection[OcrdBrowser]:
        ...

    async def first(self, *, owner: str, workspace: str) -> OcrdBrowser | None:
        ...

    async def count(self) -> int:
        ...
