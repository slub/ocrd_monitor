import asyncio
import logging

from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine

from ocrdmonitor.protocols import BrowserProcessRepository, Environment

logging.getLogger(__file__).setLevel(logging.INFO)

EXPIRATION_LOOP_INTERVAL_SECONDS = 3600


def _never_cancel() -> bool:
    return False


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


async def expiration_loop(
    environment: Environment,
    cancellation_fn: Callable[[], bool] = _never_cancel,
    loop_interval: int = EXPIRATION_LOOP_INTERVAL_SECONDS,
) -> None:
    repository = (await environment.repositories()).browser_processes
    while not cancellation_fn():
        logging.getLogger(__file__).info("Running expiration loop")
        await shutdown_expired(
            repository, environment.settings.ocrd_browser.timeout, datetime.now
        )
        await asyncio.sleep(loop_interval)
