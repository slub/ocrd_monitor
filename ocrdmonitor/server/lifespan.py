import asyncio
from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncIterator, Callable

from fastapi import FastAPI

from ocrdbrowser import OcrdBrowser
from ocrdmonitor.protocols import BrowserProcessRepository, Environment

Lifespan = Callable[[FastAPI], AsyncContextManager[None]]


def lifespan(environment: Environment) -> Lifespan:
    @asynccontextmanager
    async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
        repositories = await environment.repositories()
        await clean_unreachable_browsers(repositories.browser_processes)
        yield

    return _lifespan


async def clean_unreachable_browsers(repo: BrowserProcessRepository) -> None:
    all_browsers = await repo.find()
    async with asyncio.TaskGroup() as group:
        for browser in all_browsers:
            group.create_task(ping_or_delete(repo, browser))


async def ping_or_delete(repo: BrowserProcessRepository, browser: OcrdBrowser) -> None:
    try:
        await browser.client().get("/")
    except ConnectionError:
        await repo.delete(browser)
