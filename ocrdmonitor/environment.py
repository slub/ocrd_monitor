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
from ocrdmonitor.ocrdcontroller import OcrdController
from ocrdmonitor.protocols import (
    BrowserProcessRepository,
    JobRepository,
    RemoteServer,
    Repositories,
)
from ocrdmonitor.server.settings import Settings
from ocrdmonitor.sshremote import SSHRemote

BrowserType = Type[SubProcessOcrdBrowser] | Type[DockerOcrdBrowser]
CreatingFactories: dict[str, Callable[[set[int]], OcrdBrowserFactory]] = {
    "native": SubProcessOcrdBrowserFactory,
    "docker": functools.partial(DockerOcrdBrowserFactory, "http://localhost"),
}

RestoringFactories: dict[str, BrowserType] = {
    "native": SubProcessOcrdBrowser,
    "docker": DockerOcrdBrowser,
}


class ProductionEnvironment:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def repositories(self) -> Repositories:
        await database.init(self.settings.db_connection_string)
        restoring_factory = RestoringFactories[self.settings.ocrd_browser.mode]
        return Repositories(
            database.MongoBrowserProcessRepository(restoring_factory),
            database.MongoJobRepository(),
        )

    def browser_factory(self) -> OcrdBrowserFactory:
        port_range_set = set(range(*self.settings.ocrd_browser.port_range))
        return CreatingFactories[self.settings.ocrd_browser.mode](port_range_set)

    def controller_server(self) -> RemoteServer:
        return SSHRemote(self.settings.ocrd_controller)
