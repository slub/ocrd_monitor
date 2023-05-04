from typing import Collection, Protocol


class BrowserProcess(Protocol):
    @property
    def process_id(self) -> str:
        ...

    @property
    def workspace(self) -> str:
        ...

    @property
    def owner(self) -> str:
        ...


class BrowserProcessRepository(Protocol):
    async def insert(self, browser: BrowserProcess) -> None:
        ...

    async def delete(self, browser: BrowserProcess) -> None:
        ...

    async def find(
        self, owner: str, workspace: str, process_id: str | None = None
    ) -> Collection[BrowserProcess]:
        ...
