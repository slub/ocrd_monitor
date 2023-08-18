from datetime import datetime, timedelta
from typing import Iterable

import pytest


class ProcessSpy:
    def __init__(self, last_accessed: datetime = datetime.now()) -> None:
        self.running = True
        self.last_access_time = last_accessed

    async def stop(self) -> None:
        self.running = False


async def shutdown_old_processes(
    running_processes: Iterable[ProcessSpy], process_timeout: timedelta, now: datetime
) -> list[ProcessSpy]:
    async def stop(p: ProcessSpy) -> ProcessSpy:
        await p.stop()
        return p

    return [
        await stop(process)
        for process in running_processes
        if process.last_access_time + process_timeout <= now
    ]


@pytest.mark.asyncio
async def test__when_a_process_is_not_accessed_for_a_long_time__it_will_be_shut_down() -> (
    None
):
    process_timeout = timedelta(days=1)
    way_back = datetime.now()
    recently = datetime.now() + process_timeout / 2
    now = way_back + process_timeout

    old_process = ProcessSpy(last_accessed=way_back)
    recent_process = ProcessSpy(last_accessed=recently)
    running_processes = [old_process, recent_process]

    stopped_processes = await shutdown_old_processes(
        running_processes, process_timeout, now
    )

    assert not old_process.running
    assert recent_process.running
    assert stopped_processes == [old_process]
