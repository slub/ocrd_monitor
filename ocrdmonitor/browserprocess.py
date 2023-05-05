from typing import Collection, Protocol


class BrowserProcess(Protocol):
    def process_id(self) -> str:
        ...

    def workspace(self) -> str:
        ...

    def owner(self) -> str:
        ...


class BrowserProcessRepository(Protocol):
    async def insert(self, browser: BrowserProcess) -> None:
        ...

    async def delete(self, browser: BrowserProcess) -> None:
        ...

    async def find(
        self,
        *,
        owner: str | None = None,
        workspace: str | None = None,
        process_id: str | None = None,
    ) -> Collection[BrowserProcess]:
        ...
