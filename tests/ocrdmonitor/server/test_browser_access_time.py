from datetime import datetime, timedelta

import pytest

from ocrdbrowser import OcrdBrowser, OcrdBrowserFactory
from ocrdmonitor.protocols import BrowserProcessRepository
from tests.ocrdmonitor.server.fixtures.environment import Fixture
from tests.ocrdmonitor.server.fixtures.settings import WORKSPACE_DIR


class ClockStub:
    def __init__(self, time: datetime) -> None:
        self.time = time

    def advance_time(self, minutes=0, days=1) -> datetime:
        self.time += timedelta(minutes=minutes, days=days)
        return self.time

    def __call__(self) -> datetime:
        return self.time


@pytest.mark.asyncio
async def test__when_launching_a_new_browser__its_access_time_is_now(
    repository_fixture: Fixture,
) -> None:
    insert_time = datetime(2023, 8, 18, 12, 37)
    clock = ClockStub(insert_time)

    fixture = repository_fixture.with_clock(clock)

    async with fixture as env:
        browser_repo = (await env.repositories()).browser_processes
        browser = await insert_browser(env.browser_factory(), browser_repo)

        await browser_repo.insert(browser)
        clock.advance_time()

        last_access_time = await access_time_of_first_browser(browser_repo)
        assert last_access_time == insert_time


@pytest.mark.asyncio
async def test__finding_a_specific_browser__updates_the_last_access_time(
    repository_fixture: Fixture,
) -> None:
    insert_time = datetime(2023, 8, 18, 12, 37)
    clock = ClockStub(insert_time)

    fixture = repository_fixture.with_clock(clock)

    async with fixture as env:
        browser_repo = (await env.repositories()).browser_processes
        browser = await insert_browser(env.browser_factory(), browser_repo)

        update_time = clock.advance_time()
        _ = await browser_repo.first(
            owner=browser.owner(), workspace=browser.workspace()
        )

        clock.advance_time()
        last_access_time = await access_time_of_first_browser(browser_repo)
        assert last_access_time == update_time


async def insert_browser(
    browser_factory: OcrdBrowserFactory, browser_repo: BrowserProcessRepository
) -> OcrdBrowser:
    session_id = "the-owner"
    workspace = "a_workspace"
    full_workspace = WORKSPACE_DIR / workspace
    browser = await browser_factory(session_id, str(full_workspace))

    await browser_repo.insert(browser)
    return browser


async def access_time_of_first_browser(
    browser_repo: BrowserProcessRepository,
) -> datetime:
    browsers_and_times = await browser_repo.browsers_by_access_time()
    _, last_access_time = browsers_and_times[0]
    return last_access_time
