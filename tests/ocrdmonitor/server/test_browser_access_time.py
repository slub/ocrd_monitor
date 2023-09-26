from datetime import datetime
from typing import cast

import pytest

from ocrdbrowser import OcrdBrowserFactory
from ocrdmonitor.protocols import BrowserProcessRepository
from tests.ocrdmonitor.fixtures.environment import Fixture
from tests.ocrdmonitor.fixtures.settings import WORKSPACE_DIR
from tests.testdoubles import BrowserTestDouble, ClockStub


@pytest.mark.asyncio
async def test__browsers_inserted_at_different_times__can_retrieve_browser_inserted_before_time(
    repository_fixture: Fixture,
) -> None:
    insert_time = datetime(2023, 8, 18, 12, 37)
    clock = ClockStub(insert_time)

    fixture = repository_fixture.with_clock(clock)

    async with fixture as env:
        browser_repo = (await env.repositories()).browser_processes
        browser = await insert_browser(env.browser_factory(), browser_repo)

        new_time = clock.advance_time()
        await browser_repo.insert(browser)

        assert await browser_repo.browsers_accessed_before(new_time) == [browser]


async def insert_browser(
    browser_factory: OcrdBrowserFactory,
    browser_repo: BrowserProcessRepository,
    workspace: str = "a_workspace",
) -> BrowserTestDouble:
    session_id = "the-owner"
    full_workspace = WORKSPACE_DIR / workspace
    browser = await browser_factory(session_id, str(full_workspace))

    await browser_repo.insert(browser)
    return cast(BrowserTestDouble, browser)
