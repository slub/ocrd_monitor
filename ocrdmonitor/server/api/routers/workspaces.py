from pathlib import Path

from fastapi import APIRouter, Response
from ocrdbrowser import workspace
from ocrdmonitor.server.settings import OcrdBrowserSettings

from typing import List

class ResultList():
    def __init__(self, results: List[Path]):
        self.results = results

def router(
    browser_settings: OcrdBrowserSettings
) -> None:
    router = APIRouter(prefix="/workspaces")

    @router.get("/", name="api.list.workspaces")
    def list_workspaces(search: str | None = None) -> Response:
        spaces = [
            Path(space).relative_to(browser_settings.workspace_dir)
            for space in workspace.list_all(browser_settings.workspace_dir)
        ]

        if search:
            spaces = list(filter(lambda workspace: search in str(workspace), spaces))

        return ResultList(spaces)
    
    return router