from __future__ import annotations

import asyncio
import atexit
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, BaseSettings, validator

from ocrdbrowser import (
    DockerOcrdBrowserFactory,
    OcrdBrowserFactory,
    SubProcessOcrdBrowserFactory,
)

from ocrdmonitor.ocrdcontroller import RemoteServer
from ocrdmonitor.sshremote import SSHRemote


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

    def factory(self) -> OcrdBrowserFactory:
        port_range_set = set(range(*self.port_range))
        if self.mode == "native":
            return SubProcessOcrdBrowserFactory(port_range_set)
        else:
            factory = DockerOcrdBrowserFactory("http://localhost", port_range_set)

            @atexit.register
            def stop_containers() -> None:
                asyncio.get_event_loop().run_until_complete(factory.stop_all())

            return factory

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
