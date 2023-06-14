import asyncio
from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncIterator, Callable

from fastapi import FastAPI

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.browserprocess import BrowserProcessRepository
from ocrdmonitor.server.settings import OcrdBrowserSettings


Lifespan = Callable[[FastAPI], AsyncContextManager[None]]


def lifespan(browser_settings: OcrdBrowserSettings) -> Lifespan:
    @asynccontextmanager
    async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
        await clean_unreachable_browsers(browser_settings)
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
