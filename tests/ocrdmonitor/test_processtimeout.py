import asyncio
from datetime import datetime, timedelta
from typing import Callable

import pytest
from ocrdmonitor.protocols import BrowserProcessRepository

from tests.ocrdmonitor.fixtures.environment import Fixture
from tests.ocrdmonitor.server.test_browser_access_time import insert_browser
from tests.testdoubles import ClockStub


class ProcessSpy:
    def __init__(self, last_accessed: datetime = datetime.now()) -> None:
        self.running = True
        self.last_access_time = last_accessed

    async def stop(self) -> None:
        self.running = False


async def shutdown_old_processes(
    running_processes: BrowserProcessRepository,
    process_timeout: timedelta,
    clock: Callable[[], datetime],
) -> None:
    old_processes = await running_processes.browsers_accessed_before(
        clock() - process_timeout
    )
    async with asyncio.TaskGroup() as group:
        for process in old_processes:
            group.create_task(process.stop())
            group.create_task(running_processes.delete(process))


@pytest.mark.asyncio
async def test__when_a_process_is_not_accessed_for_a_long_time__it_will_be_shut_down(
    repository_fixture: Fixture,
) -> (None):
    process_timeout = timedelta(days=1)
    way_back = datetime.now()

    clock = ClockStub(way_back)
    fixture = repository_fixture.with_clock(clock)
    async with fixture as env:
        browser_repo = (await env.repositories()).browser_processes
        factory = env.browser_factory()

        first = await insert_browser(factory, browser_repo, "a_workspace")
        clock.advance_time(process_timeout + timedelta(seconds=1))

        second = await insert_browser(factory, browser_repo, "second_workspace")

        await shutdown_old_processes(browser_repo, process_timeout, clock)

        assert not first.is_running
        assert second.is_running
        assert await browser_repo.find() == [second]
