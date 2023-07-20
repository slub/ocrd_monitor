import asyncio
from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncIterator, Callable

from fastapi import FastAPI

import ocrdmonitor.database as database
from ocrdmonitor.repositories import BrowserProcessRepository
from ocrdmonitor.server.settings import Settings, OcrdBrowserSettings
from ocrdbrowser import OcrdBrowser


Lifespan = Callable[[FastAPI], AsyncContextManager[None]]


def lifespan(settings: Settings) -> Lifespan:
    @asynccontextmanager
    async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
        await database.init(settings.db_connection_string)
        await clean_unreachable_browsers(settings.ocrd_browser)
        yield

    return _lifespan


async def clean_unreachable_browsers(browser_settings: OcrdBrowserSettings) -> None:
    repo = await browser_settings.repository()
    all_browsers = await repo.find()
    async with asyncio.TaskGroup() as group:
        for browser in all_browsers:
            group.create_task(ping_or_delete(repo, browser))


async def ping_or_delete(repo: BrowserProcessRepository, browser: OcrdBrowser) -> None:
    try:
        await browser.client().get("/")
    except ConnectionError:
        await repo.delete(browser)
