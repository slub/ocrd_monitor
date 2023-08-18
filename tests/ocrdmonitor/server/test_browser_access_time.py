from datetime import datetime

import pytest

from tests.ocrdmonitor.server.fixtures.environment import Fixture
from tests.ocrdmonitor.server.fixtures.settings import WORKSPACE_DIR


@pytest.mark.asyncio
async def test__when_launching_a_new_browser__its_access_time_is_now(
    repository_fixture: Fixture,
) -> None:
    session_id = "the-owner"
    workspace = "a_workspace"
    full_workspace = WORKSPACE_DIR / workspace

    now = datetime(2023, 8, 18, 12, 37)

    def clock() -> datetime:
        return now

    fixture = repository_fixture.with_session_id(session_id).with_clock(clock)

    async with fixture as env:
        factory = env.browser_factory()
        browser = await factory(session_id, full_workspace)

        browser_repo = (await env.repositories()).browser_processes
        await browser_repo.insert(browser)

        last_access_time = await browser_repo.last_access_time_for(browser)
        assert last_access_time == now
