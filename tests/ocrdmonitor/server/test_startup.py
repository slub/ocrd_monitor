import pytest

from tests.ocrdmonitor.server.fixtures.environment import Fixture
from tests.testdoubles import BrowserSpy, unreachable_browser


@pytest.mark.asyncio
@pytest.mark.no_auto_repository
async def test__browsers_in_db__on_startup__cleans_unreachables_from_db() -> None:
    session_id = "the-owner"
    reachable = BrowserSpy(owner=session_id, address="http://reachable.com")
    unreachable = unreachable_browser(
        owner=session_id, address="http://unreachable.com"
    )

    async with (
        Fixture()
        .with_running_browsers(reachable, unreachable)
        .with_session_id(session_id)
    ) as env:
        assert await env.repository.count() == 1
