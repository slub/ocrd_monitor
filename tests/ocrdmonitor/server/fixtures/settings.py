from pathlib import Path

from ocrdmonitor.server.settings import (
    OcrdBrowserSettings,
    OcrdLogViewSettings,
    OcrdManagerSettings,
    Settings,
)

JOB_DIR = Path(__file__).parent / "ocrd.jobs"
WORKSPACE_DIR = Path("tests") / "workspaces"


def create_settings() -> Settings:
    return Settings(
        monitor_db_connection_string="",
        ocrd_browser=OcrdBrowserSettings(
            workspace_dir=WORKSPACE_DIR,
            port_range=(9000, 9100),
        ),
        ocrd_logview=OcrdLogViewSettings(port=8022),
        ocrd_manager=OcrdManagerSettings(url="https://manager.ocrdhost.com")
    )
