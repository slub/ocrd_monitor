from contextlib import asynccontextmanager
from typing import Callable
from ocrdmonitor.protocols import Environment
from ocrdmonitor.server import lifespan
from ocrdmonitor.server.lifespan import processtimeout, unreachable_cleanup


def _run_once() -> Callable[[], bool]:
    times_ran = 0

    def __run_once() -> bool:
        nonlocal times_ran
        times_ran = 1
        return times_ran <= 1

    return __run_once


def dev_lifespan(environment: Environment) -> lifespan.Lifespan:
    return lifespan.create(
        setup=[unreachable_cleanup.clean_unreachable_browsers(environment)],
        background=[
            processtimeout.expiration_loop(
                environment,
                cancellation_fn=_run_once(),
                loop_interval=0,
            )
        ],
    )
