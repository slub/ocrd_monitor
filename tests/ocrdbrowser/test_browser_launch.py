import asyncio
import functools
from typing import AsyncIterator, Callable, NamedTuple

import pytest
import pytest_asyncio

from ocrdbrowser import (
    DockerOcrdBrowserFactory,
    NoPortsAvailableError,
    OcrdBrowserFactory,
    SubProcessOcrdBrowserFactory,
)
from tests import markers
from tests.decorators import compose


create_docker_browser_factory = functools.partial(
    DockerOcrdBrowserFactory, "http://localhost"
)

browser_factory_test = compose(
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.parametrize(
        "create_browser_factory",
        (
            pytest.param(
                create_docker_browser_factory,
                marks=markers.skip_if_no_docker,
            ),
            pytest.param(
                SubProcessOcrdBrowserFactory, marks=markers.skip_if_no_browse_ocrd
            ),
        ),
    ),
)


class DockerProcessKiller(NamedTuple):
    kill: str = "docker stop"
    ps: str = "docker ps"


class NativeProcessKiller(NamedTuple):
    kill: str = "kill"
    ps: str = "ps"


async def kill_processes(
    killer: NativeProcessKiller | DockerProcessKiller, name_filter: str
) -> None:
    kill_cmd, ps_cmd = killer
    cmd = await asyncio.create_subprocess_shell(
        f"{kill_cmd} $({ps_cmd} | grep {name_filter} | awk '{{ print $1 }}')",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await cmd.wait()


@pytest_asyncio.fixture(autouse=True)
async def stop_browsers() -> AsyncIterator[None]:
    yield

    async with asyncio.TaskGroup() as group:
        group.create_task(kill_processes(DockerProcessKiller(), "ocrd-browser"))
        group.create_task(kill_processes(NativeProcessKiller(), "broadwayd"))
        group.create_task(kill_processes(NativeProcessKiller(), "browse-ocrd"))


CreateBrowserFactory = Callable[[set[int]], OcrdBrowserFactory]


@browser_factory_test
async def test__factory__launches_new_browser_instance(
    create_browser_factory: CreateBrowserFactory,
) -> None:
    sut = create_browser_factory({9000})
    browser = await sut("the-owner", "tests/workspaces/a_workspace")

    client = browser.client()
    response = await client.get("/")
    assert response is not None


@browser_factory_test
async def test__launching_on_an_allocated_port__raises_unavailable_port_error(
    create_browser_factory: CreateBrowserFactory,
) -> None:
    _factory = create_browser_factory({9000})
    await _factory("first-owner", "tests/workspaces/a_workspace")

    sut = create_browser_factory({9000})
    with pytest.raises(NoPortsAvailableError):
        await sut("second-owner", "tests/workspaces/a_workspace")


@browser_factory_test
async def test__one_port_allocated__launches_on_next_available(
    create_browser_factory: CreateBrowserFactory,
) -> None:
    _factory = create_browser_factory({9000})
    await _factory("other-owner", "tests/workspaces/a_workspace")

    sut = create_browser_factory({9000, 9001})
    browser = await sut("second-other-owner", "tests/workspaces/a_workspace")

    assert browser.address() == "http://localhost:9001"
