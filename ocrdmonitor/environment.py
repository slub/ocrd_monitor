import functools
from typing import Callable, NamedTuple, Type

from ocrdbrowser import (
    DockerOcrdBrowser,
    DockerOcrdBrowserFactory,
    OcrdBrowserFactory,
    SubProcessOcrdBrowser,
    SubProcessOcrdBrowserFactory,
)
from ocrdmonitor import database
from ocrdmonitor.repositories import BrowserProcessRepository
from ocrdmonitor.server.settings import Settings

BrowserType = Type[SubProcessOcrdBrowser] | Type[DockerOcrdBrowser]
CreatingFactories: dict[str, Callable[[set[int]], OcrdBrowserFactory]] = {
    "native": SubProcessOcrdBrowserFactory,
    "docker": functools.partial(DockerOcrdBrowserFactory, "http://localhost"),
}

RestoringFactories: dict[str, BrowserType] = {
    "native": SubProcessOcrdBrowser,
    "docker": DockerOcrdBrowser,
}


class Repositories(NamedTuple):
    browser_processes: BrowserProcessRepository
    ocrd_jobs: Type[database.OcrdJob]


class Environment:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def repositories(self) -> Repositories:
        await database.init(self.settings.db_connection_string)
        restoring_factory = RestoringFactories[self.settings.ocrd_browser.mode]
        return Repositories(
            database.MongoBrowserProcessRepository(restoring_factory), database.OcrdJob
        )

    def browser_factory(self) -> OcrdBrowserFactory:
        port_range_set = set(range(*self.settings.ocrd_browser.port_range))
        return CreatingFactories[self.settings.ocrd_browser.mode](port_range_set)
