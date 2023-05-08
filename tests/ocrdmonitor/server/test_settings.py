import os
from typing import Any, Literal, Type
from unittest.mock import patch

import pytest
from ocrdbrowser import DockerOcrdBrowserFactory, SubProcessOcrdBrowserFactory
from ocrdmonitor.server.settings import (
    OcrdBrowserSettings,
    OcrdControllerSettings,
    OcrdLogViewSettings,
    Settings,
)


EXPECTED = Settings(
    ocrd_browser=OcrdBrowserSettings(
        mode="native",
        workspace_dir="path/to/workdir",
        port_range=(9000, 9100),
        db_connection_string="user@mongo:mongodb:1234"
    ),
    ocrd_controller=OcrdControllerSettings(
        job_dir="path/to/jobdir",
        host="controller.ocrdhost.com",
        user="controller_user",
        port=22,
        keyfile=".ssh/id_rsa",
    ),
    ocrd_logview=OcrdLogViewSettings(
        port=22,
    ),
)


def expected_to_env() -> dict[str, str]:
    def to_dict(setting_name: str, settings: dict[str, Any]) -> dict[str, str]:
        return {
            f"OCRD_{setting_name}__{key.upper()}": str(value)
            for key, value in settings.items()
        }

    return dict(
        **to_dict("BROWSER", EXPECTED.ocrd_browser.dict()),
        **to_dict("CONTROLLER", EXPECTED.ocrd_controller.dict()),
        **to_dict("LOGVIEW", EXPECTED.ocrd_logview.dict()),
    )


@patch.dict(os.environ, expected_to_env())
def test__can_parse_env() -> None:
    sut = Settings()

    assert sut == EXPECTED


@pytest.mark.parametrize(
    argnames=["mode", "factory_type"],
    argvalues=[
        ("native", SubProcessOcrdBrowserFactory),
        ("docker", DockerOcrdBrowserFactory),
    ],
)
@patch.dict(os.environ, expected_to_env())
def test__browser_settings__produces_matching_factory_for_selected_mode(
    mode: Literal["native"] | Literal["docker"], factory_type: Type[Any]
) -> None:
    sut = Settings()
    sut.ocrd_browser.mode = mode

    actual = sut.ocrd_browser.factory()
    assert isinstance(actual, factory_type)
