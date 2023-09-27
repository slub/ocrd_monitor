import asyncio

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.protocols import BrowserProcessRepository, Environment


async def clean_unreachable_browsers(environment: Environment) -> None:
    repo = (await environment.repositories()).browser_processes
    all_browsers = await repo.find()
    async with asyncio.TaskGroup() as group:
        for browser in all_browsers:
            group.create_task(ping_or_delete(repo, browser))


async def ping_or_delete(repo: BrowserProcessRepository, browser: OcrdBrowser) -> None:
    try:
        await browser.client().get("/")
    except ConnectionError:
        await repo.delete(browser)
