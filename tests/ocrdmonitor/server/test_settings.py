from datetime import timedelta
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

from ocrdmonitor.server.settings import (
    OcrdBrowserSettings,
    OcrdControllerSettings,
    OcrdLogViewSettings,
    OcrdManagerSettings,
    Settings,
)


TIMEOUT_DAYS = 1
TIMEOUT_HOURS = 2
TIMEOUT_MINUTES = 20
BROWSER_TIMEOUT = timedelta(
    days=TIMEOUT_DAYS, hours=TIMEOUT_HOURS, minutes=TIMEOUT_MINUTES
)
BROWSER_TIMEOUT_SETTINGS_STRING = (
    f"P{TIMEOUT_DAYS}DT{TIMEOUT_HOURS}H{TIMEOUT_MINUTES}M0S"
)


EXPECTED = Settings(
    monitor_db_connection_string="user@mongo:mongodb:1234",
    ocrd_browser=OcrdBrowserSettings(
        mode="native",
        timeout=BROWSER_TIMEOUT,
        workspace_dir=Path("path/to/workdir"),
        port_range=(9000, 9100),
    ),
    ocrd_controller=OcrdControllerSettings(
        host="controller.ocrdhost.com",
        user="controller_user",
        port=22,
        keyfile=Path(".ssh/id_rsa"),
    ),
    ocrd_logview=OcrdLogViewSettings(
        port=22,
    ),
    ocrd_manager=OcrdManagerSettings(
        url="https://manager.ocrdhost.com",
    ),
)


def expected_to_env() -> dict[str, str]:
    def stringify(value: Any) -> str:
        if value is BROWSER_TIMEOUT:
            return BROWSER_TIMEOUT_SETTINGS_STRING

        return str(value)

    def to_dict(setting_name: str, settings: dict[str, Any]) -> dict[str, str]:
        return {
            f"OCRD_{setting_name}__{key.upper()}": stringify(value)
            for key, value in settings.items()
        }

    return dict(
        MONITOR_DB_CONNECTION_STRING=EXPECTED.monitor_db_connection_string,
        **to_dict("BROWSER", EXPECTED.ocrd_browser.model_dump()),
        **to_dict("CONTROLLER", EXPECTED.ocrd_controller.model_dump()),
        **to_dict("LOGVIEW", EXPECTED.ocrd_logview.model_dump()),
        **to_dict("MANAGER", EXPECTED.ocrd_manager.model_dump()),
    )


@patch.dict(os.environ, expected_to_env())
def test__can_parse_env() -> None:
    import pprint

    pprint.pprint(expected_to_env())
    sut = Settings()

    assert sut == EXPECTED
