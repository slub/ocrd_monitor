from __future__ import annotations

import functools
from pathlib import Path
from typing import Callable, Literal, Type

from pydantic import BaseModel, BaseSettings, validator

from ocrdbrowser import (
    DockerOcrdBrowser,
    DockerOcrdBrowserFactory,
    OcrdBrowserFactory,
    SubProcessOcrdBrowserFactory,
    SubProcessOcrdBrowser,
)
from ocrdmonitor import dbmodel
from ocrdmonitor.browserprocess import BrowserProcessRepository

from ocrdmonitor.ocrdcontroller import RemoteServer
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


class OcrdControllerSettings(BaseModel):
    job_dir: Path
    host: str
    user: str
    port: int = 22
    keyfile: Path = Path.home() / ".ssh" / "id_rsa"

    def controller_remote(self) -> RemoteServer:
        return SSHRemote(self)


class OcrdLogViewSettings(BaseModel):
    port: int


class OcrdBrowserSettings(BaseModel):
    workspace_dir: Path
    mode: Literal["native", "docker"] = "native"
    port_range: tuple[int, int]
    db_connection_string: str

    async def repository(self) -> BrowserProcessRepository:
        # if not self._repository_initialized:
        await dbmodel.init(self.db_connection_string)

        restore = RestoringFactories[self.mode]
        return dbmodel.MongoBrowserProcessRepository(restore)

    def factory(self) -> OcrdBrowserFactory:
        port_range_set = set(range(*self.port_range))
        return CreatingFactories[self.mode](port_range_set)

    @validator("port_range", pre=True)
    def validator(cls, value: str | tuple[int, int]) -> tuple[int, int]:
        if isinstance(value, str):
            split_values = (
                value.replace("[", "")
                .replace("]", "")
                .replace("(", "")
                .replace(")", "")
                .split(",")
            )
            int_pair = tuple(int(v) for v in split_values)
        else:
            int_pair = value

        if len(int_pair) != 2:
            raise ValueError("Port range must have exactly two values")

        return int_pair  # type: ignore


class Settings(BaseSettings):
    ocrd_browser: OcrdBrowserSettings
    ocrd_controller: OcrdControllerSettings
    ocrd_logview: OcrdLogViewSettings

    class Config:
        env_nested_delimiter = "__"
