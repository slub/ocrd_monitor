from fastapi.testclient import TestClient

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.server.app import create_app
from tests.ocrdmonitor.server.decorators import use_custom_repository
from tests.ocrdmonitor.server.fixtures.app import create_settings
from tests.ocrdmonitor.server.fixtures.repository import (
    RepositoryInitializer,
    patch_repository,
)
from tests.testdoubles import BrowserSpy


@use_custom_repository
async def test__browsers_in_db__on_startup__cleans_unreachables_from_db(
    repository: RepositoryInitializer,
) -> None:
    reachable = BrowserSpy(address="http://reachable.com")
    unreachable = BrowserSpy(address="http://unreachable.com")
    unreachable.configure_client(response=ConnectionError)

    def factory(
        owner: str, workspace: str, address: str, process_id: str
    ) -> OcrdBrowser:
        if "unreachable" in address:
            return unreachable
        else:
            return reachable

    async with repository(factory) as repo:
        async with patch_repository(repo):
            await repo.insert(unreachable)
            await repo.insert(reachable)

            with TestClient(create_app(create_settings())):
                pass

            assert await repo.count() == 1
