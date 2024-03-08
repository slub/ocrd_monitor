from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any, Callable, Literal, Type

from pydantic import BaseModel, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from ocrdbrowser import (
    DockerOcrdBrowser,
    DockerOcrdBrowserFactory,
    OcrdBrowserFactory,
    SubProcessOcrdBrowser,
    SubProcessOcrdBrowserFactory,
)

BrowserType = Type[SubProcessOcrdBrowser] | Type[DockerOcrdBrowser]
CreatingFactories: dict[str, Callable[[set[int]], OcrdBrowserFactory]] = {
    "native": SubProcessOcrdBrowserFactory,
    "docker": functools.partial(DockerOcrdBrowserFactory, "http://localhost"),
}

RestoringFactories: dict[str, BrowserType] = {
    "native": SubProcessOcrdBrowser,
    "docker": DockerOcrdBrowser,
}


class OcrdManagerSettings(BaseSettings):
    url: str

class OcrdLogViewSettings(BaseSettings):
    port: int

class OcrdBrowserSettings(BaseSettings):
    workspace_dir: Path
    mode: Literal["native", "docker"] = "native"
    port_range: tuple[int, int]

    @field_validator("port_range", mode="before")
    @classmethod
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

        if not int_pair or len(int_pair) != 2:
            raise ValueError("Port range must have exactly two values")

        return int_pair


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    monitor_db_connection_string: str

    ocrd_browser: OcrdBrowserSettings
    ocrd_logview: OcrdLogViewSettings
    ocrd_manager: OcrdManagerSettings

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, OcrdEnvSource(settings_cls))


COMPLEX_MODELS = {OcrdBrowserSettings}


def getargs(field_name: str, model_type: Type[BaseModel]) -> dict[str, str]:
    fields_to_env = {
        model_field_name: f"{field_name}__{model_field_name}".upper()
        for model_field_name in model_type.model_fields
    }
    return {
        field: os.environ.get(var, "") for field, var in fields_to_env.items()
    }


class OcrdEnvSource(EnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        if field.annotation in COMPLEX_MODELS:
            return getargs(field_name, field.annotation)

        return super().prepare_field_value(field_name, field, value, value_is_complex)
