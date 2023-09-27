import asyncio
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Callable,
    Coroutine,
    Iterable,
)

from fastapi import FastAPI


Lifespan = Callable[[FastAPI], AsyncContextManager[None]]
Tasks = Iterable[Coroutine[Any, Any, Any]]


def create(setup: Tasks = (), background: Tasks = ()) -> Lifespan:
    @asynccontextmanager
    async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
        # we're using task group here, because asyncio
        # only stores weak refs to tasks and cleans them up
        # if they aren't referenced anywhere. See:
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        async with asyncio.TaskGroup() as group:
            for task in setup:
                group.create_task(task)

        async with asyncio.TaskGroup() as group:
            for task in background:
                group.create_task(task)

            yield

    return _lifespan
