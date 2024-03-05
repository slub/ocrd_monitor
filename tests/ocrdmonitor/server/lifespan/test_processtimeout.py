from datetime import datetime, timedelta

import pytest

from ocrdmonitor.server.lifespan import processtimeout

from tests.ocrdmonitor.fixtures.environment import Fixture
from tests.ocrdmonitor.server.test_browser_access_time import insert_browser
from tests.testdoubles import ClockStub


@pytest.mark.asyncio
async def test__when_a_process_is_not_accessed_for_a_long_time__it_will_be_shut_down(
    browser_fixture: Fixture,
) -> (None):
    process_timeout = timedelta(days=1)
    way_back = datetime.now()

    clock = ClockStub(way_back)
    fixture = browser_fixture.with_clock(clock)
    async with fixture as env:
        browser_repo = (await env.repositories()).browser_processes
        factory = env.browser_factory()

        first = await insert_browser(factory, browser_repo, "a_workspace")
        clock.advance_time(process_timeout + timedelta(seconds=1))

        second = await insert_browser(factory, browser_repo, "second_workspace")

        clock.advance_time(process_timeout)
        await processtimeout.shutdown_expired(browser_repo, process_timeout, clock)

        assert not first.is_running
        assert second.is_running
        assert await browser_repo.find() == [second]
