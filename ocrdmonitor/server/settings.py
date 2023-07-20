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
from ocrdmonitor.database import _browserprocessrepository
from ocrdmonitor.repositories import BrowserProcessRepository

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
    host: str
    user: str
    port: int = 22
    keyfile: Path = Path.home() / ".ssh" / "id_rsa"


class OcrdLogViewSettings(BaseModel):
    port: int


class OcrdBrowserSettings(BaseModel):
    workspace_dir: Path
    mode: Literal["native", "docker"] = "native"
    port_range: tuple[int, int]

    async def repository(self) -> BrowserProcessRepository:
        restore = RestoringFactories[self.mode]
        return _browserprocessrepository.MongoBrowserProcessRepository(restore)

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
    db_connection_string: str

    ocrd_browser: OcrdBrowserSettings
    ocrd_controller: OcrdControllerSettings
    ocrd_logview: OcrdLogViewSettings

    class Config:
        env_nested_delimiter = "__"
