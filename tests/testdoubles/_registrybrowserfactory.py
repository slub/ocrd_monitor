from types import TracebackType
from typing import NewType, Self, Type, cast

from ocrdbrowser import OcrdBrowser

from ._browserfactory import (
    BrowserTestDouble,
    BrowserTestDoubleFactory,
    IteratingBrowserTestDoubleFactory,
)

BrowserRegistry = NewType("BrowserRegistry", dict[str, BrowserTestDouble])


class RegistryBrowserFactory:
    @classmethod
    def iteratingfactory(cls: Type[Self], browser_registry: BrowserRegistry) -> Self:
        return cls(IteratingBrowserTestDoubleFactory(), browser_registry)

    def __init__(
        self,
        internal_factory: BrowserTestDoubleFactory,
        browser_registry: BrowserRegistry,
    ) -> None:
        self._factory = internal_factory
        self._registry = browser_registry

    async def __aenter__(self) -> Self:
        await self._factory.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._factory.__aexit__(exc_type, exc_value, traceback)

    async def __call__(self, owner: str, workspace_path: str) -> OcrdBrowser:
        browser = await self._factory(owner, workspace_path)
        self._registry[browser.address()] = cast(BrowserTestDouble, browser)
        return browser


class RestoringRegistryBrowserFactory:
    def __init__(self, browser_registry: BrowserRegistry) -> None:
        self._registry = browser_registry

    def __call__(
        self, owner: str, workspace: str, address: str, process_id: str
    ) -> BrowserTestDouble:
        browser = self._registry[address]
        return browser
