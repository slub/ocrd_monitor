import asyncio

from datetime import datetime, timedelta
from typing import Callable

from ocrdmonitor.backgroundprocess import BackgroundProcess
from ocrdmonitor.environment import ProductionEnvironment
from ocrdmonitor.protocols import BrowserProcessRepository, Environment
from ocrdmonitor.server.settings import Settings


EXPIRATION_LOOP_INTERVAL_SECONDS = 3600


async def shutdown_expired(
    repository: BrowserProcessRepository,
    process_timeout: timedelta,
    clock: Callable[[], datetime],
) -> None:
    old_processes = await repository.browsers_accessed_before(clock() - process_timeout)
    async with asyncio.TaskGroup() as group:
        for process in old_processes:
            group.create_task(process.stop())
            group.create_task(repository.delete(process))


async def expiration_loop(environment: Environment) -> None:
    repository = (await environment.repositories()).browser_processes
    while True:
        await shutdown_expired(
            repository, environment.settings.ocrd_browser.timeout, datetime.now
        )
        await asyncio.sleep(EXPIRATION_LOOP_INTERVAL_SECONDS)


def background_main() -> None:
    env = ProductionEnvironment(Settings())
    asyncio.run(expiration_loop(env))


def browser_cleanup_process() -> BackgroundProcess:
    return BackgroundProcess(background_main)
